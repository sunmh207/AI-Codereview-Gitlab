"""Multi-turn agent loop."""
from __future__ import annotations

import logging
import os
from typing import Any

from biz.agent.llm_adapter import LLMAdapter
from biz.agent.tool_registry import ToolRegistry
from biz.utils.token_util import count_tokens, truncate_text_by_tokens

logger = logging.getLogger(__name__)


class TokenBudgetExceeded(Exception):
    """Raised when the cumulative token estimate for the conversation exceeds the cap."""


class InvalidToolCallStreak(Exception):
    """Raised when the agent emits 3 consecutive rounds with no usable tool calls or text."""


class AgentRunner:
    def __init__(
        self,
        *,
        adapter: LLMAdapter,
        registry: ToolRegistry,
        max_iterations: int = 20,
        total_token_cap: int = 80_000,
        tool_output_max_tokens: int | None = None,
    ) -> None:
        self.adapter = adapter
        self.registry = registry
        self.max_iterations = max_iterations
        self.total_token_cap = total_token_cap
        self.tool_output_max_tokens = (
            tool_output_max_tokens
            if tool_output_max_tokens is not None
            else int(os.getenv("AGENT_TOOL_OUTPUT_MAX_TOKENS", "10000"))
        )

    def run(
        self,
        initial_messages: list[dict],
        out: dict[str, Any] | None = None,
    ) -> str:
        messages = list(initial_messages)
        last_assistant_content: str | None = None
        # Tracks rounds where LLM emitted nothing actionable (no content AND no tool_calls).
        # After 3 in a row, raise to trigger soft-degrade.
        empty_streak = 0
        iterations_used = 0
        try:
            for i in range(self.max_iterations):
                iterations_used = i + 1
                resp = self.adapter.completions_with_tools(
                    messages=messages,
                    tools=self.registry.list_schemas(),
                )
                logger.info("agent round %d: tool_calls=%d content_len=%d",
                            i, len(resp.tool_calls), len(resp.content or ""))
                if resp.content:
                    last_assistant_content = resp.content
                if not resp.tool_calls:
                    if not (resp.content or "").strip():
                        # Empty round (model emitted only invalid/empty tool calls or nothing at all).
                        empty_streak += 1
                        if empty_streak >= 3:
                            raise InvalidToolCallStreak(
                                f"3 consecutive empty rounds from LLM"
                            )
                        continue
                    return resp.content or last_assistant_content or ""
                # Productive round: reset streak.
                empty_streak = 0
                messages.append(self.adapter.build_assistant_message(resp))
                for call in resp.tool_calls:
                    result = self.registry.dispatch(call)
                    # Truncate tool output to bound message size.
                    if result.success and self.tool_output_max_tokens > 0:
                        truncated = truncate_text_by_tokens(result.output, self.tool_output_max_tokens)
                        if truncated != result.output:
                            result = result.__class__(
                                success=True,
                                output=truncated + "\n[output truncated]",
                                error=result.error,
                            )
                    messages.append(self.adapter.build_tool_message(call, result))
                    # Token accounting.
                    usage = self._estimate_total_tokens(messages)
                    if usage > self.total_token_cap:
                        raise TokenBudgetExceeded(
                            f"token estimate {usage} exceeds cap {self.total_token_cap}"
                        )
            return last_assistant_content or f"max iterations ({self.max_iterations}) reached without final response"
        finally:
            if out is not None:
                out["iterations"] = iterations_used
                out["messages"] = messages

    @staticmethod
    def _estimate_total_tokens(messages: list[dict]) -> int:
        total = 0
        for m in messages:
            content = m.get("content") or ""
            if isinstance(content, str):
                total += count_tokens(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        total += count_tokens(str(part))
        return total