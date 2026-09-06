import pytest

from clearglassinc_sdk.agent import Agent
from clearglassinc_sdk.exceptions import GuardrailViolation, MaxStepsExceeded, ToolExecutionError
from clearglassinc_sdk.guardrails import MaxLengthGuardrail, RequiredKeywordsGuardrail
from clearglassinc_sdk.runner import Runner
from clearglassinc_sdk.testing import FakeLLMClient, text_response, tool_call_response
from clearglassinc_sdk.tools import tool


def make_agent_with_ping_tool() -> Agent:
    agent = Agent(name="Test Agent", instructions="Be helpful.")

    @tool(description="Returns pong")
    def ping() -> str:
        return "pong"

    agent.add_tool(ping)
    return agent


def test_run_plain_text_response():
    agent = Agent(name="Test Agent", instructions="Be helpful.")
    client = FakeLLMClient(responses=[text_response("hello back")])
    runner = Runner(agent, client)

    result = runner.run("hello")
    assert result.output == "hello back"
    assert result.steps == 1
    assert agent.memory.history()[0].content == "hello"


def test_run_executes_tool_calls_then_answers():
    agent = make_agent_with_ping_tool()
    client = FakeLLMClient(
        responses=[
            tool_call_response("call_1", "ping", {}),
            text_response("pong received"),
        ]
    )
    runner = Runner(agent, client)

    result = runner.run("call ping")
    assert result.output == "pong received"
    assert result.steps == 2
    tool_messages = [m for m in agent.memory.history() if m.role == "tool"]
    assert tool_messages[0].content == "pong"


def test_run_wraps_tool_exceptions():
    agent = Agent(name="Test Agent", instructions="Be helpful.")

    @tool()
    def boom() -> str:
        raise RuntimeError("kaboom")

    agent.add_tool(boom)
    client = FakeLLMClient(responses=[tool_call_response("call_1", "boom", {})])
    runner = Runner(agent, client)

    with pytest.raises(ToolExecutionError):
        runner.run("do it")


def test_run_raises_on_unknown_tool_call_without_crashing():
    agent = Agent(name="Test Agent", instructions="Be helpful.")
    client = FakeLLMClient(
        responses=[
            tool_call_response("call_1", "nonexistent", {}),
            text_response("done"),
        ]
    )
    runner = Runner(agent, client)

    result = runner.run("do it")
    assert result.output == "done"
    tool_messages = [m for m in agent.memory.history() if m.role == "tool"]
    assert "no such tool" in tool_messages[0].content


def test_run_enforces_max_steps():
    agent = Agent(name="Test Agent", instructions="Be helpful.", max_steps=2)

    @tool()
    def loopy() -> str:
        return "again"

    agent.add_tool(loopy)
    client = FakeLLMClient(
        default_response=tool_call_response("call_x", "loopy", {}),
    )
    runner = Runner(agent, client)

    with pytest.raises(MaxStepsExceeded):
        runner.run("loop forever")


def test_input_guardrail_blocks_before_calling_llm():
    agent = Agent(name="Test Agent", instructions="Be helpful.")
    agent.input_guardrails = [RequiredKeywordsGuardrail(keywords=["allowed"])]
    client = FakeLLMClient(responses=[text_response("should not be reached")])
    runner = Runner(agent, client)

    with pytest.raises(GuardrailViolation):
        runner.run("forbidden topic")
    assert client.calls == []


def test_output_guardrail_blocks_final_answer():
    agent = Agent(name="Test Agent", instructions="Be helpful.")
    agent.output_guardrails = [MaxLengthGuardrail(max_chars=3)]
    client = FakeLLMClient(responses=[text_response("way too long")])
    runner = Runner(agent, client)

    with pytest.raises(GuardrailViolation):
        runner.run("hi")


def test_run_stream_yields_final_chunk():
    agent = Agent(name="Test Agent", instructions="Be helpful.")
    client = FakeLLMClient(responses=[text_response("streamed output")])
    runner = Runner(agent, client)

    chunks = list(runner.run_stream("hi"))
    assert "".join(c.delta for c in chunks) == "streamed output"
    assert agent.memory.history()[-1].content == "streamed output"


async def test_arun_plain_text_response():
    agent = Agent(name="Test Agent", instructions="Be helpful.")
    client = FakeLLMClient(responses=[text_response("async hello")])
    runner = Runner(agent, client)

    result = await runner.arun("hi")
    assert result.output == "async hello"


async def test_arun_executes_tool_calls():
    agent = make_agent_with_ping_tool()
    client = FakeLLMClient(
        responses=[
            tool_call_response("call_1", "ping", {}),
            text_response("async pong received"),
        ]
    )
    runner = Runner(agent, client)

    result = await runner.arun("call ping")
    assert result.output == "async pong received"


async def test_arun_stream_yields_final_chunk():
    agent = Agent(name="Test Agent", instructions="Be helpful.")
    client = FakeLLMClient(responses=[text_response("async streamed")])
    runner = Runner(agent, client)

    chunks = [chunk async for chunk in runner.arun_stream("hi")]
    assert "".join(c.delta for c in chunks) == "async streamed"
