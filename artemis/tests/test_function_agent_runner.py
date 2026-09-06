from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path

import pytest

from artemis.function_agent import (
    AgentRunner,
    ExecutionStatus,
    RunStatus,
    RuntimeSettings,
    build_runtime,
)
from artemis.function_agent.llm_clients import (
    ChatMessage,
    LLMResponse,
    LLMStreamEvent,
    MessageRole,
    ToolCall,
)


class FakeLLMClient:
    def __init__(self) -> None:
        self.complete_calls = 0
        self.stream_calls = 0
        self.last_tools: Sequence[dict[str, object]] = []

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, object]],
    ) -> LLMResponse:
        self.last_tools = tools
        self.complete_calls += 1
        if self.complete_calls == 1:
            return LLMResponse(
                tool_calls=[ToolCall(id="ping-call", name="system.ping", arguments={})],
                finish_reason="tool_calls",
            )
        assert messages[-1].role is MessageRole.TOOL
        return LLMResponse(text="Artemis is operational.", finish_reason="stop")

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, object]],
    ) -> AsyncIterator[LLMStreamEvent]:
        self.last_tools = tools
        self.stream_calls += 1
        if self.stream_calls == 1:
            call = ToolCall(id="stream-ping", name="system.ping", arguments={})
            yield LLMStreamEvent(type="tool_call", tool_call=call)
            yield LLMStreamEvent(
                type="completed",
                response=LLMResponse(tool_calls=[call], finish_reason="tool_calls"),
            )
            return
        assert messages[-1].role is MessageRole.TOOL
        yield LLMStreamEvent(type="text_delta", text_delta="Operational")
        yield LLMStreamEvent(
            type="completed",
            response=LLMResponse(text="Operational", finish_reason="stop"),
        )


@pytest.mark.asyncio
async def test_runner_executes_tool_loop_with_strict_schemas(tmp_path: Path) -> None:
    runtime = build_runtime(
        RuntimeSettings(
            workspace=tmp_path / "workspace",
            state_dir=tmp_path / "state",
            approval_secret="r" * 64,
        )
    )
    client = FakeLLMClient()
    runner = AgentRunner(runtime.agent, client)

    result = await runner.run("Check agent health")

    assert result.status is RunStatus.COMPLETED
    assert result.text == "Artemis is operational."
    assert result.turns == 2
    assert len(result.tool_results) == 1
    assert result.tool_results[0].status is ExecutionStatus.SUCCEEDED
    ping_schema = next(
        item for item in client.last_tools if item["function"]["name"] == "system.ping"
    )
    assert ping_schema["function"]["strict"] is True


@pytest.mark.asyncio
async def test_runner_stream_preserves_multi_turn_tool_execution(tmp_path: Path) -> None:
    runtime = build_runtime(
        RuntimeSettings(
            workspace=tmp_path / "workspace",
            state_dir=tmp_path / "state",
            approval_secret="r" * 64,
        )
    )
    client = FakeLLMClient()
    runner = AgentRunner(runtime.agent, client)

    events = [event async for event in runner.stream("Stream health status")]

    event_types = [event.type for event in events]
    assert "runner.tool_result" in event_types
    assert "runner.completed" in event_types
    tool_event = next(event for event in events if event.type == "runner.tool_result")
    assert tool_event.metadata["result"]["status"] == "succeeded"
    assert client.stream_calls == 2
