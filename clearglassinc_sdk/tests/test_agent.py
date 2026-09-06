import pytest

from clearglassinc_sdk.agent import Agent
from clearglassinc_sdk.tools import tool


def make_agent() -> Agent:
    return Agent(name="Test Agent", instructions="Be helpful.")


def test_add_tool_and_list_tools():
    agent = make_agent()

    @tool()
    def ping() -> str:
        return "pong"

    agent.add_tool(ping)
    assert agent.list_tools() == ["ping"]
    assert agent.get_tool("ping") is ping
    assert agent.get_tool("missing") is None


def test_add_tool_rejects_duplicate_names():
    agent = make_agent()

    @tool(name="ping")
    def ping_a() -> str:
        return "a"

    @tool(name="ping")
    def ping_b() -> str:
        return "b"

    agent.add_tool(ping_a)
    with pytest.raises(ValueError):
        agent.add_tool(ping_b)


def test_tool_schemas_reflect_registered_tools():
    agent = make_agent()

    @tool(description="Adds two numbers")
    def add(a: int, b: int) -> int:
        return a + b

    agent.add_tool(add)
    schemas = agent.tool_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "add"
    assert schemas[0]["description"] == "Adds two numbers"
