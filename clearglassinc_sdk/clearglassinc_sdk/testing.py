"""Test doubles for exercising the SDK without hitting a real LLM provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from clearglassinc_sdk.clients.base import CompletionResult, LLMClient, ToolCall
from clearglassinc_sdk.memory import Message


@dataclass
class FakeLLMClient(LLMClient):
    """A scripted `LLMClient` for unit tests and offline examples.

    `responses` is consumed in order, one per call to `complete`/`acomplete`.
    If `responses` is exhausted, `default_response` (or an echo of the last
    user message) is returned instead.
    """

    responses: list[CompletionResult] = field(default_factory=list)
    default_response: CompletionResult | None = None
    calls: list[list[Message]] = field(default_factory=list, init=False)
    _index: int = field(default=0, init=False)

    def _next(self, messages: list[Message]) -> CompletionResult:
        self.calls.append(messages)
        if self._index < len(self.responses):
            result = self.responses[self._index]
            self._index += 1
            return result
        if self.default_response is not None:
            return self.default_response
        last_user = next((m for m in reversed(messages) if m.role == "user"), None)
        echo = last_user.content if last_user else ""
        return CompletionResult(content=f"echo: {echo}")

    def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> CompletionResult:
        return self._next(messages)


def tool_call_response(call_id: str, tool_name: str, arguments: dict[str, Any]) -> CompletionResult:
    """Convenience builder for a scripted tool-call turn."""
    return CompletionResult(
        content="",
        tool_calls=[ToolCall(id=call_id, name=tool_name, arguments=arguments)],
    )


def text_response(content: str) -> CompletionResult:
    """Convenience builder for a scripted plain-text turn."""
    return CompletionResult(content=content)
