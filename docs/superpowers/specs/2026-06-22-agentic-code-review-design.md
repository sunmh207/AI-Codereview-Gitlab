# Agentic Code Review Design

- **Date**: 2026-06-22
- **Status**: Approved (pending implementation)
- **Author**: brainstorm session with user

## 1. Background & Motivation

Currently when the system receives a Merge Request / Pull Request / Push webhook, it sends only the diff to the LLM for review. The LLM has no access to the rest of the project, so it cannot:

- See how the changed code is actually used elsewhere
- Detect when a deleted function still has callers
- Understand the conventions and patterns of the surrounding code
- Catch inconsistencies between the diff and the rest of the codebase

The desired enhancement is to let the review have access to the **whole project**, not just the diff. The chosen approach is **agentic**: give the LLM tool-use capabilities so it can explore the project itself, deciding which files to read and which commands to run.

## 2. Goals

- Provide a second review strategy (`agentic`) that complements the existing `diff_only` strategy.
- The agent can read project files, run AST queries, and execute sandboxed shell commands (which exposes `ls`, `rg`/`grep`, `tree`, etc. without needing dedicated tools).
- All three platforms (GitLab, GitHub, Gitea) and all event types (MR/PR/push) work with agentic mode.
- Selection between strategies is configuration-driven; a deployment picks one strategy at a time.
- Soft-degrade to `diff_only` on failure so users always get at least the current-quality review.

## 3. Non-Goals

- No vector embeddings / RAG in v1. The LLM decides what to read.
- No cross-review memory or learning across sessions.
- No mixing strategies within a single review.
- No native tool-calling for every provider; a JSON-protocol fallback covers providers without tool-use support.
- No real-time repo watcher / cron poller; sync happens lazily on webhook events.

## 4. Architecture Overview

```
Webhook (any platform)
        │
        ▼
   biz/queue/worker.py
        │  (selects strategy based on REVIEW_STRATEGY env var)
        │
   ┌────┴─────┐
   ▼          ▼
 CodeReviewer  AgenticReviewer (new)
 (diff_only,    │
  existing)     ▼
            LocalRepoSyncer (new)
                │
                ▼
            AgentRunner (new)
                │
        ┌───────┴────────┐
        ▼                ▼
   ToolRegistry     LLMAdapter (new)
   + 3 tools        (wraps existing Factory)
        │
        ▼
   Local repo at data/repo_cache/<provider>_<owner>_<repo>/
```

All new code lives under `biz/agent/`. The only changes to existing code:

1. `biz/llm/client/base.py` — extend `completions()` to return structured output with `tool_calls`.
2. `biz/queue/worker.py` — branch on `REVIEW_STRATEGY` to pick `CodeReviewer` or `AgenticReviewer`.
3. `conf/prompt_templates.yml` — add `agentic_code_review_prompt` template.

## 5. Components

### 5.1 `LLMAdapter`

Wraps the existing `Factory().getClient()` and normalizes output across providers.

```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]
    raw: Any
```

`completions(messages, tools=...)` accepts OpenAI-style tool schemas. Native tool-use is used for providers that support it (OpenAI, Anthropic, DeepSeek, Qwen). Providers without native tool-use (ZhipuAI, Ollama with small models) fall back to a **JSON protocol**: the system prompt instructs the model to emit `{"tool": "...", "args": {...}}` JSON blocks; the adapter parses these into `ToolCall` objects.

### 5.2 `Tool` Abstract Base

```python
class Tool(abc.ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema

    @abc.abstractmethod
    def execute(self, **kwargs) -> ToolResult: ...

@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
```

Tool output text is bounded (default 10000 tokens, `AGENT_TOOL_OUTPUT_MAX_TOKENS`). Truncated output is prefixed with `[output truncated]`.

### 5.3 `ToolRegistry`

```python
class ToolRegistry:
    def register(self, tool: Tool): ...
    def list_schemas(self) -> list[dict]: ...
    def dispatch(self, call: ToolCall) -> ToolResult: ...
```

### 5.4 `AgentRunner`

Multi-turn loop core. Calls LLM, parses tool calls, dispatches them, appends results to messages, repeats until the LLM returns without tool calls or `max_iterations` is reached.

Pseudocode:

```
messages = initial_messages
for i in range(max_iterations):
    resp = llm_adapter.completions(messages, tools=registry.list_schemas())
    if not resp.tool_calls:
        return resp.content
    # assistant message format depends on provider:
    #   - native tool-use providers: {"role": "assistant", "content": ..., "tool_calls": [...]}
    #   - JSON-protocol fallback:   {"role": "assistant", "content": "...JSON blocks..."}
    # LLMAdapter abstracts this via build_assistant_message(resp).
    messages.append(adapter.build_assistant_message(resp))
    for call in resp.tool_calls:
        result = registry.dispatch(call)
        # tool message format: {"role": "tool", "tool_call_id": call.id, "content": str(result)}
        messages.append(adapter.build_tool_message(call, result))
return last_assistant_content or "max iterations reached"
```

### 5.5 `LocalRepoSyncer`

Lazy clone/update of the target repository to `data/repo_cache/<provider>_<owner>_<repo>/`.

- First sync for a project: `git clone <url>` (full clone, **not** `--depth=1`, so any historical SHA can be checked out).
- Subsequent syncs: `git fetch --all --prune` then `git checkout <ref>` (or `git reset --hard <sha>` for push events). Working tree lives inside the clone itself; checkout switches the working tree in place.
- Concurrency note: since each review runs in its own worker subprocess, two simultaneous reviews on the same project may race. Mitigation: the syncer takes a per-project file lock (`data/repo_cache/<key>.lock`) with `fcntl.flock`; second waiter waits up to 60s then proceeds even if lock acquisition fails (logged as warning).
- Sync runs synchronously inside the existing worker subprocess; the webhook has already returned 200.
- Failure to sync → soft-degrade to `diff_only`.

### 5.6 `AgenticReviewer`

Top-level entry point used by `worker.py`. Mirrors `CodeReviewer.review_and_strip_code` so swapping is a one-line change at the call site.

```python
class AgenticReviewer:
    def review(self, diffs_text: str, commits_text: str) -> str:
        ...
```

Factory method `build_from_event(webhook_data, ...)` infers `provider / project / ref`, invokes `LocalRepoSyncer.sync_to(...)`, returns an instance bound to the repo root.

## 6. Data Flow (single MR review)

1. GitLab webhook → `/review/webhook` (existing).
2. `handle_queue` spawns worker subprocess (existing).
3. `handle_merge_request_event` fetches changes + commits (existing).
4. Branch on `REVIEW_STRATEGY`:
   - `diff_only` → existing `CodeReviewer` path.
   - `agentic` → `AgenticReviewer.review()`:
     a. `LocalRepoSyncer.sync_to(provider, project, source_sha)` returns repo root.
     b. `AgentRunner.run(messages)` executes the multi-turn loop:
        - Round 1: LLM → `read_file(path="src/billing.py")` → runner reads file → tool message.
        - Round 2: LLM → `run_command(cmd="rg InvoiceService -n")` → runner greps → tool message.
        - ... up to 20 rounds ...
        - Round N: LLM → content="<review report>" → loop exits.
     c. Return review text.
5. Worker posts review as a note on the MR (existing).
6. Worker emits `merge_request_reviewed` event with score parsed from review text (existing).

## 7. Tools (3)

After streamlining, the tool set is:

| Tool | Purpose | Why kept |
|---|---|---|
| `read_file` | Read file with offset/limit (lines) | Structured params + binary detection + line numbering |
| `ast_query` | Semantic queries (definitions, references, callees) for Python in v1 | Shell cannot do AST-level queries |
| `run_command` | Sandboxed shell execution | Escape hatch + covers `ls`/`rg`/`tree` that the dropped tools would have provided |

### 7.1 `read_file(path, offset=0, limit=500)`

- Returns `"lines N-M:\n<content>"`.
- Binary files (NUL byte ratio > 10% in first 8KB) return `error="binary file"`.
- Path sandboxing enforced at tool level: any path outside `repo_root` returns `error="path outside repo root"`.

### 7.2 `ast_query(query, path=".")`

v1 only supports Python (using Python stdlib `ast` for definitions and callees; `rg` + AST-node-type validation for references). Tree-sitter is a future option for multi-language support but is **not** used in v1 to keep dependencies small. Exposes three sub-queries:

- `definitions` — list functions and classes under `path` (file or directory).
- `references <symbol>` — find all references to a symbol across the repo; uses `rg` for candidates and validates via Python `ast` that each match is an actual reference (not a string literal, comment, etc.).
- `callees <func_name>` — list function calls inside the named function using Python `ast`.

`path` may be a single file or a directory; directories are walked recursively. Other languages return `error="language not supported in v1"` without raising.

### 7.3 `run_command(cmd, timeout=30)`

Sandboxed shell. Safety layers (defense in depth):

1. **Working directory** forced to `repo_root`.
2. **Path-traversal regex** rejects `cd ..`, absolute paths outside repo, redirection to external paths.
3. **Command allowlist** (default): `ls, cat, head, tail, find, rg, grep, wc, tree, file, stat, diff, git log/show/diff/blame/ls-files/ls-tree, python -c '<single-line expr>'`.
4. **Command blocklist** (default): `rm, mv, cp (to external), chmod, chown, sudo, curl, wget, ssh, dd, mkfs, mount, kubectl, docker, npm install, pip install, ...`.
5. **Sensitive path patterns** blocked: `.git/`, `.env`, `id_rsa`, `*.pem`.
6. **Timeout** (default 30s) enforced via `subprocess.run(..., timeout=...)`.

Blocklist is checked first; if a command matches both, it is rejected. Both lists are overridable via `AGENT_SHELL_ALLOWLIST` and `AGENT_SHELL_BLOCKLIST` env vars.

## 8. Configuration

| Variable | Default            | Description |
|---|--------------------|---|
| `REVIEW_STRATEGY` | `diff_only`        | `diff_only` or `agentic`. One per deployment. |
| `AGENT_MAX_ITERATIONS` | `20`               | Agent loop max rounds. |
| `AGENT_TOOL_OUTPUT_MAX_TOKENS` | `10000`            | Per-tool output cap. |
| `REPO_CACHE_DIR` | `data/repo_cache/` | Local cache root. |
| `GIT_CLONE_TIMEOUT` | `120`              | Seconds before clone/fetch fails. |
| `AGENT_SHELL_ALLOWLIST` | (built-in default) | Override default allowlist. |
| `AGENT_SHELL_BLOCKLIST` | (built-in default) | Override default blocklist. |

`REVIEW_STRATEGY` is set once per deployment. Mixing strategies within a single review is not supported.

## 9. Error Handling

| Failure | Behavior |
|---|---|
| `git clone` or `fetch` fails | Log + IM notify + soft-degrade to `diff_only` |
| LLM call fails (inside agent loop) | Log + soft-degrade to `diff_only`; the outer worker handler still has its existing IM-notify-on-exception behavior if the outer try/except fires |
| Tool execution throws | Caught, returned as `ToolResult(success=False, error=...)`; LLM sees error in next round |
| Shell command timeout | Returned as `ToolResult(success=False, error="timed out after 30s")` |
| Shell sandbox violation | Returned as `ToolResult(success=False, error="blocked by sandbox")` |
| `max_iterations` reached | Loop exits; last assistant content (or generic message) returned as review |
| 3 consecutive invalid tool_calls | Loop exits with error + soft-degrade to `diff_only` |
| Total token estimate exceeds hard cap | Soft-degrade to `diff_only`. Hard cap hardcoded to **80k tokens** in v1 (rationale: keeps within typical 128k-context models with headroom; revisit via env var in v2 if needed) |

Soft-degrade is implemented inside `AgenticReviewer.review()` via a try/except wrapping the entire agent loop; on failure it calls `CodeReviewer().review_and_strip_code(...)` so users always receive at least the current-quality review.

## 10. Security

- System prompt explicitly instructs the LLM to ignore any instructions found in diff/commit text.
- Path sandboxing enforced at tool level, not by parsing shell strings.
- Sensitive paths (`.env`, `.git/`, `*.pem`, etc.) refused by `read_file` and `ast_query` regardless of caller.
- Shell sandbox has both allowlist and blocklist; blocklist takes precedence on conflict.
- No cleaning of tool output: code is code, any "instructions" found in it are evaluated by the LLM at its own risk.

## 11. Logging

Each review produces a single structured log line (JSON):

```json
{
  "event": "agentic_review",
  "project": "group/myapp",
  "ref": "feature/foo",
  "strategy": "agentic",
  "iterations": 7,
  "total_tokens_est": 23000,
  "tool_calls": [
    {"tool": "read_file", "args": {"path": "src/billing.py"}, "duration_ms": 12, "output_tokens_est": 1500},
    {"tool": "run_command", "args": {"cmd": "rg InvoiceService -n"}, "duration_ms": 340, "output_tokens_est": 800}
  ],
  "duration_ms": 45200,
  "review_result_length": 2300,
  "score": 85,
  "degraded": false
}
```

## 12. Testing Strategy

### 12.1 Unit Tests

- `tests/agent/tools/test_read_file.py` — normal read, offset/limit, binary detection, path sandboxing, sensitive paths, missing files.
- `tests/agent/tools/test_ast_query.py` — Python `definitions`, `references`, `callees`; non-Python returns error.
- `tests/agent/tools/test_run_command.py` — allowlist pass-through, blocklist rejection, path-traversal rejection, timeout, non-zero exit, sensitive paths.
- `tests/agent/test_safety.py` — path normalization, sensitive pattern matching, shell tokenization.
- `tests/agent/test_runner.py` — single-round termination, multi-round flow, max_iterations termination, exception isolation, mock LLM with `unittest.mock`.
- `tests/agent/test_llm_adapter.py` — native tool-use parsing (OpenAI-style), JSON-protocol fallback parsing, error propagation.
- `tests/agent/test_repo_syncer.py` — first clone, incremental fetch, timeout (mocked `subprocess.run`).

### 12.2 Integration Tests

- `tests/agent/test_integration.py` — small Python project under `tmp_path`; mock LLM follows a scripted call sequence; verify message accumulation and final result.
- `tests/agent/test_degradation.py` — verify soft-degrade triggers on syncer failure, LLM failure, and 3x invalid tool_calls.

### 12.3 End-to-End Tests

- `tests/agent/test_e2e_webhook.py` — fake GitLab MR payload with `REVIEW_STRATEGY=agentic`; mock HTTP for LLM and for posting note; verify full flow.

### 12.4 Manual Smoke Tests (acceptance checklist)

1. First-clone of an uncached project.
2. Incremental fetch on a second push.
3. Degradation by setting `GIT_CLONE_TIMEOUT=1`.
4. max_iterations termination (mock LLM that always returns tool_call).
5. Shell sandbox rejection of `cat /etc/passwd`.
6. Shell timeout with `sleep 60`.
7. Real 1GB+ project completes without error.

### 12.5 Coverage Targets

- `biz/agent/`: ≥ 80% line coverage.
- `biz/agent/safety.py`: 100% line coverage.
- `biz/agent/runner.py`: ≥ 90% line coverage.

### 12.6 Out of Scope for Tests

- Real LLM behavior (covered only in manual smoke).
- Upstream SDK behavior.
- Git command semantics (assumed correct; we test how we call it).

## 13. Resource Estimates (for ops docs)

- Disk: ~10MB–2GB per cached project; provision ≥ 50GB.
- Memory: peak ~500MB per concurrent agent session.
- Tokens: 5k–50k per review (3–10× `diff_only`).
- Latency: 30s–5min per review.

## 14. Implementation Plan Reference

Detailed task breakdown will be produced by the `writing-plans` skill after this spec is approved.