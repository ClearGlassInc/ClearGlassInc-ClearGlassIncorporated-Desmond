"""Provider-agnostic LLM client contract.

Every provider adapter (OpenAI, Anthropic, ...) implements `LLMClient` so the
`Runner` never has to know which vendor it's talking to. Both sync and async,
streaming and non-streaming calls are supported.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

from clearglassinc_sdk.memory import Message


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class CompletionResult:
    """A single model turn: text content and/or tool calls to execute."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """One incremental piece of a streaming completion."""

    delta: str
    done: bool = False
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(ABC):
    """Abstract base for LLM provider adapters."""

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> CompletionResult:
        """Synchronous, non-streaming completion."""
        raise NotImplementedError

    async def acomplete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> CompletionResult:
        """Async completion. Default implementation delegates to `complete`
        via a thread so adapters only need to implement one path if desired."""
        import asyncio

        return await asyncio.to_thread(
            self.complete,
            messages,
            system=system,
            tools=tools,
            model=model,
            temperature=temperature,
        )

    def stream(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Iterator[StreamChunk]:
        """Synchronous streaming completion. Default falls back to a single
        chunk built from `complete` for adapters that don't implement true
        streaming."""
        result = self.complete(
            messages, system=system, tools=tools, model=model, temperature=temperature
        )
        yield StreamChunk(delta=result.content, done=True, tool_calls=result.tool_calls)

    async def astream(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """Async streaming completion. Default falls back to a single chunk."""
        result = await self.acomplete(
            messages, system=system, tools=tools, model=model, temperature=temperature
        )
        yield StreamChunk(delta=result.content, done=True, tool_calls=result.tool_calls)
