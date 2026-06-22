"""LLM output normalization across providers (placeholder)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]
    raw: Any = None