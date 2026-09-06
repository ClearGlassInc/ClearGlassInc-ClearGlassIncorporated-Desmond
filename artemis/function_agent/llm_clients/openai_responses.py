# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""OpenAI Responses API adapter for the vendor-neutral LLMClient contract."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

from .base import (
    ChatMessage,
    LLMResponse,
    LLMStreamEvent,
    MessageRole,
    ToolCall,
)


class OpenAIAdapterError(RuntimeError):
    pass


class OpenAIResponsesClient:
    """Async OpenAI Responses API adapter with function calling and SSE streaming."""

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
        client: Any | None = None,
    ) -> None:
        self.model = model
        if client is not None:
            self._client = client
            return
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise OpenAIAdapterError(
                "Install the optional OpenAI adapter with: pip install -e '.[openai]'"
            ) from exc
        options: dict[str, Any] = {
            "api_key": api_key,
            "timeout": timeout_seconds,
        }
        if base_url is not None:
            options["base_url"] = base_url
        self._client = AsyncOpenAI(**options)

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]],
    ) -> LLMResponse:
        instructions, input_items = self._build_input(messages)
        request: dict[str, Any] = {
            "model": self.model,
            "input": input_items,
            "tools": self._normalize_tools(tools),
        }
        if instructions:
            request["instructions"] = instructions
        response = await self._client.responses.create(**request)
        return self._parse_response(response)

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]],
    ) -> AsyncIterator[LLMStreamEvent]:
        instructions, input_items = self._build_input(messages)
        request: dict[str, Any] = {
            "model": self.model,
            "input": input_items,
            "tools": self._normalize_tools(tools),
            "stream": True,
        }
        if instructions:
            request["instructions"] = instructions

        stream = await self._client.responses.create(**request)
        async for event in stream:
            event_type = str(getattr(event, "type", "unknown"))
            if event_type == "response.output_text.delta":
                yield LLMStreamEvent(
                    type="text_delta",
                    text_delta=str(getattr(event, "delta", "")),
                    metadata={"provider_event": event_type},
                )
                continue
            if event_type == "response.completed":
                parsed = self._parse_response(event.response)
                for tool_call in parsed.tool_calls:
                    yield LLMStreamEvent(
                        type="tool_call",
                        tool_call=tool_call,
                        metadata={"provider_event": event_type},
                    )
                yield LLMStreamEvent(
                    type="completed",
                    response=parsed,
                    metadata={"provider_event": event_type},
                )
                continue
            if event_type in {"response.failed", "error"}:
                error = getattr(event, "error", None)
                raise OpenAIAdapterError(f"OpenAI stream failed: {error or event_type}")
            yield LLMStreamEvent(
                type="provider_event",
                metadata={"provider_event": event_type},
            )

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result

    @staticmethod
    def _normalize_tools(tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in tools:
            function = item.get("function", item)
            normalized.append(
                {
                    "type": "function",
                    "name": function["name"],
                    "description": function.get("description", ""),
                    "parameters": function.get(
                        "parameters",
                        {"type": "object", "properties": {}, "additionalProperties": False},
                    ),
                    "strict": function.get("strict", True),
                }
            )
        return normalized

    @staticmethod
    def _build_input(messages: Sequence[ChatMessage]) -> tuple[str, list[dict[str, Any]]]:
        instructions: list[str] = []
        input_items: list[dict[str, Any]] = []
        for message in messages:
            if message.role is MessageRole.SYSTEM:
                if message.content:
                    instructions.append(message.content)
                continue
            if message.role is MessageRole.TOOL:
                if not message.tool_call_id:
                    raise OpenAIAdapterError("Tool messages require tool_call_id")
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.tool_call_id,
                        "output": message.content or "",
                    }
                )
                continue
            if message.content:
                input_items.append(
                    {
                        "role": message.role.value,
                        "content": message.content,
                    }
                )
            if message.role is MessageRole.ASSISTANT:
                for raw_call in message.metadata.get("tool_calls", []):
                    call = ToolCall.model_validate(raw_call)
                    input_items.append(
                        {
                            "type": "function_call",
                            "call_id": call.id,
                            "name": call.name,
                            "arguments": json.dumps(
                                call.arguments,
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        }
                    )
        return "\n\n".join(instructions), input_items

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        tool_calls: list[ToolCall] = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) != "function_call":
                continue
            try:
                arguments = json.loads(getattr(item, "arguments", "{}"))
            except json.JSONDecodeError as exc:
                raise OpenAIAdapterError("Model returned invalid function arguments") from exc
            if not isinstance(arguments, dict):
                raise OpenAIAdapterError("Function arguments must decode to an object")
            tool_calls.append(
                ToolCall(
                    id=str(getattr(item, "call_id", getattr(item, "id", ""))),
                    name=str(item.name),
                    arguments=arguments,
                )
            )

        usage_object = getattr(response, "usage", None)
        if usage_object is None:
            usage: dict[str, int] = {}
        elif hasattr(usage_object, "model_dump"):
            usage = {
                key: int(value)
                for key, value in usage_object.model_dump().items()
                if isinstance(value, int)
            }
        else:
            usage = {}

        return LLMResponse(
            text=str(getattr(response, "output_text", "") or ""),
            tool_calls=tool_calls,
            finish_reason=str(getattr(response, "status", "completed")),
            usage=usage,
            raw={
                "id": getattr(response, "id", None),
                "model": getattr(response, "model", None),
                "request_id": getattr(response, "_request_id", None),
            },
        )
