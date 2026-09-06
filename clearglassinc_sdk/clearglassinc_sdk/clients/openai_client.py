"""OpenAI (and OpenAI-compatible) chat completions adapter.

Requires the `openai` package (`pip install clearglassinc-sdk[openai]`). The
import is deferred to instantiation time so the base SDK has zero hard
dependency on any single provider's SDK.
"""

from __future__ import annotations

import json
from typing import Any

from clearglassinc_sdk.clients.base import CompletionResult, LLMClient, ToolCall
from clearglassinc_sdk.memory import Message


class OpenAIClient(LLMClient):
    """Adapter for OpenAI's Chat Completions API (and Azure/OpenAI-compatible
    endpoints via `base_url`)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "OpenAIClient requires the 'openai' package: pip install clearglassinc-sdk[openai]"
            ) from exc

        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.default_model = model

    def _to_openai_messages(
        self, messages: list[Message], system: str | None
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(message.to_dict() for message in messages)
        return payload

    def _to_openai_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [{"type": "function", "function": schema} for schema in tools]

    def _parse_response(self, response: Any) -> CompletionResult:
        choice = response.choices[0]
        content = choice.message.content or ""
        tool_calls: list[ToolCall] = []
        for raw_call in choice.message.tool_calls or []:
            tool_calls.append(
                ToolCall(
                    id=raw_call.id,
                    name=raw_call.function.name,
                    arguments=json.loads(raw_call.function.arguments or "{}"),
                )
            )
        return CompletionResult(content=content, tool_calls=tool_calls, raw=response)

    def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> CompletionResult:
        response = self._client.chat.completions.create(
            model=model or self.default_model,
            messages=self._to_openai_messages(messages, system),
            tools=self._to_openai_tools(tools),
            temperature=temperature,
        )
        return self._parse_response(response)

    async def acomplete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> CompletionResult:
        response = await self._async_client.chat.completions.create(
            model=model or self.default_model,
            messages=self._to_openai_messages(messages, system),
            tools=self._to_openai_tools(tools),
            temperature=temperature,
        )
        return self._parse_response(response)
