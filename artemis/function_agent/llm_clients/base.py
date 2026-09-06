# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Vendor-neutral LLM transport contracts."""
from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)
    raw: dict[str, Any] | None = None


class LLMStreamEvent(BaseModel):
    type: str
    text_delta: str = ""
    tool_call: ToolCall | None = None
    response: LLMResponse | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMClient(Protocol):
    """Adapter implemented by OpenAI, Anthropic, local, or private model clients."""

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]],
    ) -> LLMResponse: ...

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]],
    ) -> AsyncIterator[LLMStreamEvent]: ...
