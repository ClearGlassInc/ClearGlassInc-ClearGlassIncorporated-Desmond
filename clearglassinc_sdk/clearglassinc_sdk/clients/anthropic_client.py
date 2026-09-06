"""Anthropic Messages API adapter.

Requires the `anthropic` package (`pip install clearglassinc-sdk[anthropic]`).
The import is deferred to instantiation time so the base SDK has zero hard
dependency on any single provider's SDK.
"""

from __future__ import annotations

from typing import Any

from clearglassinc_sdk.clients.base import CompletionResult, LLMClient, ToolCall
from clearglassinc_sdk.memory import Message

_DEFAULT_MAX_TOKENS = 4096


class AnthropicClient(LLMClient):
    """Adapter for Anthropic's Messages API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-5",
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "AnthropicClient requires the 'anthropic' package: "
                "pip install clearglassinc-sdk[anthropic]"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self._async_client = anthropic.AsyncAnthropic(api_key=api_key)
        self.default_model = model
        self.max_tokens = max_tokens

    def _to_anthropic_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        # Anthropic has no "system" role in the messages list and no "tool"
        # role name — tool results are user-turn `tool_result` content blocks.
        payload: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                continue
            if message.role == "tool":
                payload.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_call_id,
                                "content": message.content,
                            }
                        ],
                    }
                )
            else:
                payload.append({"role": message.role, "content": message.content})
        return payload

    def _to_anthropic_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "name": schema["name"],
                "description": schema["description"],
                "input_schema": schema["parameters"],
            }
            for schema in tools
        ]

    def _parse_response(self, response: Any) -> CompletionResult:
        content = ""
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
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
        response = self._client.messages.create(
            model=model or self.default_model,
            max_tokens=self.max_tokens,
            system=system or "",
            messages=self._to_anthropic_messages(messages),
            tools=self._to_anthropic_tools(tools) or [],
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
        response = await self._async_client.messages.create(
            model=model or self.default_model,
            max_tokens=self.max_tokens,
            system=system or "",
            messages=self._to_anthropic_messages(messages),
            tools=self._to_anthropic_tools(tools) or [],
            temperature=temperature,
        )
        return self._parse_response(response)
