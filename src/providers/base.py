"""Provider-neutral chat contracts used by the assistant orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

ChatMessage = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCallRequest:
    """One local function call requested by an LLM provider."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class ProviderTurn:
    """Provider response normalized for the orchestration loop."""

    content: str | None
    tool_calls: tuple[ToolCallRequest, ...]
    assistant_message: ChatMessage


class ProviderError(RuntimeError):
    """Safe provider failure suitable for conversion to a public response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ChatProvider(Protocol):
    """Minimal interface required by the file assistant."""

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
    ) -> ProviderTurn:
        """Return the next assistant message or tool-call request."""


__all__ = [
    "ChatMessage",
    "ChatProvider",
    "ProviderError",
    "ProviderTurn",
    "ToolCallRequest",
]
