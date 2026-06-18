---
name: code-review-expert
description: "Expert code review of current git changes with a senior engineer lens. Detects SOLID violations, security risks, database migration issues, business logic flaws (idempotency, concurrency, state machines), messaging anti-patterns, and API design problems. Proposes actionable improvements aligned with the team's software design checklist."
---

# Code Review Expert

## Overview

Perform a structured review of the current git changes with focus on SOLID, architecture, database migrations, core business patterns, messaging reliability, API design, removal candidates, and security risks. Default to review-only output unless the user asks to implement changes.

## Severity Levels

| Level | Name | Criteria | Action |
|-------|------|----------|--------|
| **P0** | Critical | Must fix. Breaks service startup, causes data loss/corruption, security vulnerability, long-duration table lock blocking all business | Must block merge |
| **P1** | High | Runtime blocker. Data corruption under concurrency, workflow deadlock, OOM crash, duplicate data, transaction inconsistency | Should fix before merge |
| **P2** | Medium | Quality concern. Performance degradation, poor maintainability, long-term data quality risk, design flaws in non-critical paths | Fix in this PR or create follow-up |
| **P3** | Low | Suggestion. Naming style, minor code structure tweaks, non-critical optimization | Optional improvement |

### Severity Quick Reference

**P0 examples**: Modifying released Flyway scripts, non-idempotent migration SQL (bare ALTER/INSERT without guard), swallowed exceptions in @Transactional (no re-throw), direct DDL on large tables causing lock, SQL injection, sending MQ messages inside transaction
**P1 examples**: No concurrency control on hot resources, missing idempotency on critical endpoints, consumer without duplicate message handling, list endpoint without page size limit, state machine with dead-end paths, scheduled tasks without skip-if-running guard
**P2 examples**: Flyway naming convention violations, new table missing audit fields, detail page not split for lazy loading, single-record loop operations (non-hot path), improper snapshot/reference field design, synchronous cross-service calls
**P3 examples**: Column naming style, comment additions, minor performance suggestions on non-critical paths

## Workflow

### 1) Preflight context

- Use `git status -sb`, `git diff --stat`, and `git diff` to scope changes.
- If needed, use `rg` or `grep` to find related modules, usages, and contracts.
- Identify entry points, ownership boundaries, and critical paths (auth, payments, data writes, network).
- Classify the change type: is it a database migration, core business logic, message handler, API endpoint, or scheduled task? This determines which checklist sections to prioritize.

**Edge cases:**
- **No changes**: If `git diff` is empty, inform user and ask if they want to review staged changes or a specific commit range.
- **Large diff (>500 lines)**: Summarize by file first, then review in batches by module/feature area.
- **Mixed concerns**: Group findings by logical feature, not just file order.

### 2) Database & Flyway migration review

If the change includes SQL migration scripts or schema changes, load `references/database-checklist.md` and check:

- **[P0] Schema compatibility**: Released scripts must never be modified, renamed, split, or merged (Checksum failure = service won't start). Unreleased scripts may be consolidated.
- **[P0] SQL idempotency**: Version management does NOT replace idempotent SQL. DDL must use `IF NOT EXISTS` or project utilities (proc_add_column, etc.); DML backfills must have guard conditions (`WHERE NOT EXISTS`, `INSERT IGNORE`, scope-limiting WHERE); destructive ops need explicit justification comments.
- **[P0] Large table changes**: Tables >5M rows or >2GB require lock-avoidance strategy (ALGORITHM=INSTANT for MySQL 8.0+ append-only columns, or rename-table approach). Direct DDL on large tables causes long-duration lock blocking all business.
- **[P2] Script naming**: Version format (e.g., `V1.1.0_1__description.sql`), strict version incrementing, developer-unique identifiers.
- **[P2] DDL standards**: Audit fields (`create_time`, `update_time`) on new tables.
- **[P2] Migration restrictions**: No JavaMigration for complex data cleaning at startup; use independent task scripts.

### 3) Core business logic review (TP)

For changes touching transactional business logic, load `references/business-checklist.md` and check:

- **[P0] Transaction safety**: Core business try-catch in `@Transactional` methods must re-throw exceptions. Swallowing exceptions causes silent commit of corrupt data — extremely severe and hard to detect.
- **[P1] Concurrency control**: Hot resource contention must use distributed locks (Redis) or optimistic locking (CAS/version). Missing locks → data corruption under concurrent access.
- **[P1] Idempotency**: Critical save/update endpoints must be safe under repeated calls (Token mechanism or unique business key constraint). Missing → duplicate records on retry/double-click.
- **[P1] State machine completeness**: Approval/workflow state transitions must form a closed loop with no dead-end states. Dead-end → workflow permanently stuck.
- **[P2] Field attribute design**: Distinguish snapshot fields (historical immutable data like prices at order time) vs reference fields (live lookups by ID).
- **[P2] Critical rule snapshots**: Batch/serial number flags and unit conversion rates must be stored redundantly to prevent master data changes from corrupting inventory/finance.

### 4) Message-driven architecture review

For changes involving MQ producers or consumers, load `references/messaging-checklist.md` and check:

- **[P0] Send timing**: Messages must NEVER be sent inside `@Transactional` methods. If transaction rolls back but message already sent → permanent data inconsistency with no automatic recovery. Use `@TransactionalEventListener(phase = AFTER_COMMIT)` or `afterCommit` hook.
- **[P1] Consumer idempotency**: Message consumers must handle duplicate messages safely. Missing → duplicate business operations on message redelivery.
- **[P2] Ordering guarantees**: Order-sensitive flows (e.g., create->pay->ship) must use consistent Partition Key (e.g., OrderID).
- **[P2] Cross-service decoupling**: Cross-database/cross-service operations should use MQ with retry+compensation for eventual consistency, not synchronous calls.

### 5) API & interface design review

For changes touching API endpoints or service interfaces, load `references/api-design-checklist.md` and check:

- **[P1] List protection**: List endpoints must enforce `MaxPageSize` (e.g., 100) to prevent OOM. Unbounded queries can crash the service.
- **[P1] N+1 prevention (hot path)**: No SQL/RPC calls inside loops on frequently-called endpoints; causes timeout cascades under load.
- **[P1] Incremental updates**: Update endpoints should accept only changed fields + version for optimistic lock validation. Full overwrites → concurrent data loss.
- **[P2] N+1 prevention (non-hot path)**: Same pattern in low-frequency paths; performance concern but not immediate crash risk.
- **[P2] Batch operations**: Multi-record insert/update must use `insertList`/`batchUpdate`, not single-record loops.
- **[P3] Lazy loading**: Detail pages should split core data from expensive data (BOM/logs/large fields); expensive data loads via separate endpoint.

### 6) Scheduled task review

For changes involving scheduled/cron tasks:

- **[P1] Skip-if-running**: Tasks must configure "disallow concurrent execution" (e.g., `@DisallowConcurrentExecution` for Quartz, or XXL-Job's "ignore expired trigger"). Task pile-up causes cascade failure.
- **[P1] Distributed lock**: Multi-instance environments must use Redis/ShedLock to ensure single-node execution. Missing → same task runs N times simultaneously.
- **[P2] Null/division safety**: Aggregation calculations must handle NULL and division-by-zero with `IFNULL`/`CASE WHEN` defenses.

### 7) SOLID + architecture smells

- Load `references/solid-checklist.md` for specific prompts.
- Look for:
  - **SRP**: Overloaded modules with unrelated responsibilities.
  - **OCP**: Frequent edits to add behavior instead of extension points.
  - **LSP**: Subclasses that break expectations or require type checks.
  - **ISP**: Wide interfaces with unused methods.
  - **DIP**: High-level logic tied to low-level implementations.
- When you propose a refactor, explain *why* it improves cohesion/coupling and outline a minimal, safe split.
- If refactor is non-trivial, propose an incremental plan instead of a large rewrite.

### 8) Removal candidates + iteration plan

- Load `references/removal-plan.md` for template.
- Identify code that is unused, redundant, or feature-flagged off.
- Distinguish **safe delete now** vs **defer with plan**.
- Provide a follow-up plan with concrete steps and checkpoints (tests/metrics).

### 9) Security and reliability scan

- Load `references/security-checklist.md` for coverage.
- Check for:
  - XSS, injection (SQL/NoSQL/command), SSRF, path traversal
  - AuthZ/AuthN gaps, missing tenancy checks
  - Secret leakage or API keys in logs/env/files
  - Rate limits, unbounded loops, CPU/memory hotspots
  - Unsafe deserialization, weak crypto, insecure defaults
  - **Race conditions**: concurrent access, check-then-act, TOCTOU, missing locks
- Call out both **exploitability** and **impact**.

### 10) Code quality scan

- Load `references/code-quality-checklist.md` for coverage.
- Check for:
  - **Error handling**: swallowed exceptions, overly broad catch, missing error handling, async errors
  - **Performance**: N+1 queries, CPU-intensive ops in hot paths, missing cache, unbounded memory
  - **Boundary conditions**: null/undefined handling, empty collections, numeric boundaries, off-by-one
- Flag issues that may cause silent failures or production incidents.

### 11) Output format

**Output language (MANDATORY)**: The entire review report MUST be written in Simplified Chinese (简体中文) — all section titles, issue descriptions, suggested fixes, and summaries. Keep the following tokens untranslated as-is: severity labels (P0/P1/P2/P3), file paths and line numbers, code snippets, and fixed enum values (APPROVE / REQUEST_CHANGES / COMMENT). This applies regardless of the language of the code, commits, or these skill files.

报告结构如下（请严格使用以下中文模板，标题与正文一律用简体中文，仅保留 P0/P1/P2/P3、文件:行号、枚举值不变）：

```markdown
## 代码审查总结

**审查文件**: X 个文件，变更 Y 行
**变更类型**: [数据库迁移 / 业务逻辑 / 消息 / API / 定时任务 / 混合]
**总体评估**: [APPROVE / REQUEST_CHANGES / COMMENT]

---

## 问题清单

### P0 - 严重
（无 或 逐条列出）

### P1 - 高
1. **[文件:行号]** 简要标题
  - 问题描述
  - 修复建议

### P2 - 中
N. （跨小节连续编号，承接 P1 之后的下一项序号）
  - ...

### P3 - 低
...

---

## 删除/迭代计划
（如适用）

## 额外建议
（非阻塞性的可选改进）
```

**行内评论**: 文件级问题使用以下格式（描述用中文）：
```
::code-comment{file="path/to/file.ts" line="42" severity="P1"}
问题描述与修复建议（中文）。
::
```

**无问题时**: 若未发现问题，请用中文明确说明：
- 检查了哪些内容
- 哪些方面未覆盖（例如："未验证数据库迁移"）
- 残留风险或建议补充的测试

### 12) Next steps confirmation

After presenting findings, ask user how to proceed. Per section 11, this prompt is part of the review output and MUST also be written in Simplified Chinese (keep P0/P1/P2/P3 untranslated):

```markdown
---

## 后续步骤

本次审查发现 X 个问题（P0: _, P1: _, P2: _, P3: _）。

**你希望如何处理？**

1. **全部修复** - 我将实施所有建议的修改
2. **仅修复 P0/P1** - 仅处理严重和高优先级问题
3. **修复指定项** - 告诉我需要修复哪些问题
4. **不修改** - 审查完成，无需实施

请选择一个选项或提供具体指示。
```

**Important**: Do NOT implement any changes until user explicitly confirms. This is a review-first workflow.

## Resources

### references/

| File | Purpose |
|------|---------|
| `solid-checklist.md` | SOLID smell prompts and refactor heuristics |
| `security-checklist.md` | Web/app security and runtime risk checklist |
| `code-quality-checklist.md` | Error handling, performance, boundary conditions |
| `database-checklist.md` | Flyway migration, DDL, large table change strategy |
| `business-checklist.md` | Concurrency, idempotency, snapshots, state machines, transactions |
| `messaging-checklist.md` | MQ reliability, consumer idempotency, ordering, send timing |
| `api-design-checklist.md` | Pagination, lazy loading, batch ops, optimistic locking |
| `removal-plan.md` | Template for deletion candidates and follow-up plan |
