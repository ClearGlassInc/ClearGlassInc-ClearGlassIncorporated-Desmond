from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest

from artemis.function_agent.llm_clients import (
    ChatMessage,
    MessageRole,
    OpenAIResponsesClient,
)


@dataclass
class FakeFunctionCall:
    type: str = "function_call"
    call_id: str = "call-1"
    name: str = "system.ping"
    arguments: str = "{}"


class FakeUsage:
    def model_dump(self) -> dict[str, int]:
        return {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}


class FakeResponse:
    def __init__(self) -> None:
        self.id = "resp-1"
        self.model = "test-model"
        self.status = "completed"
        self.output_text = ""
        self.output = [FakeFunctionCall()]
        self.usage = FakeUsage()
        self._request_id = "req-1"


@dataclass
class FakeEvent:
    type: str
    delta: str = ""
    response: Any = None
    error: Any = None


class FakeStream:
    def __init__(self, events: list[FakeEvent]) -> None:
        self.events = events

    def __aiter__(self) -> AsyncIterator[FakeEvent]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[FakeEvent]:
        for event in self.events:
            yield event


class FakeResponsesResource:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    async def create(self, **request: Any) -> Any:
        self.requests.append(request)
        if request.get("stream"):
            return FakeStream(
                [
                    FakeEvent(type="response.output_text.delta", delta="Operational"),
                    FakeEvent(type="response.completed", response=FakeResponse()),
                ]
            )
        return FakeResponse()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponsesResource()


@pytest.mark.asyncio
async def test_openai_adapter_flattens_function_tools() -> None:
    fake_client = FakeOpenAIClient()
    adapter = OpenAIResponsesClient(model="test-model", client=fake_client)
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content="Operate precisely."),
        ChatMessage(role=MessageRole.USER, content="Check health."),
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "system.ping",
                "description": "Health check",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
    ]

    response = await adapter.complete(messages, tools)

    request = fake_client.responses.requests[0]
    assert request["instructions"] == "Operate precisely."
    assert request["tools"][0] == {
        "type": "function",
        "name": "system.ping",
        "description": "Health check",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    }
    assert response.tool_calls[0].name == "system.ping"
    assert response.usage["total_tokens"] == 13
    assert response.raw == {
        "id": "resp-1",
        "model": "test-model",
        "request_id": "req-1",
    }


@pytest.mark.asyncio
async def test_openai_adapter_streams_text_and_completed_calls() -> None:
    fake_client = FakeOpenAIClient()
    adapter = OpenAIResponsesClient(model="test-model", client=fake_client)

    events = [
        event
        async for event in adapter.stream(
            [ChatMessage(role=MessageRole.USER, content="Check health")],
            [],
        )
    ]

    assert events[0].type == "text_delta"
    assert events[0].text_delta == "Operational"
    assert any(event.type == "tool_call" for event in events)
    assert events[-1].type == "completed"
