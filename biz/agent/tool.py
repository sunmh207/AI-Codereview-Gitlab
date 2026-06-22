"""Tool abstract base class for the agent."""
from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    success: bool
    output: str
    error: str | None = None

    def __bool__(self) -> bool:
        # Allows `if result:` to mean "successful and non-empty output".
        return self.success and bool(self.output)


class Tool(abc.ABC):
    """Abstract base class for agent tools.

    Subclasses must define class attributes `name`, `description`, `parameters`
    (JSON Schema dict) and implement `execute(**kwargs)`.
    """
    name: str = ""
    description: str = ""
    parameters: dict = {}

    @abc.abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        ...

    def to_schema(self) -> dict:
        """Return an OpenAI-style tool schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
