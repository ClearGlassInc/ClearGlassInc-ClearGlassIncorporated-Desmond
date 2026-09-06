from clearglassinc_sdk.tools import Tool, tool


def test_tool_decorator_infers_name_and_description():
    @tool()
    def add(a: int, b: int) -> int:
        """Adds two numbers."""
        return a + b

    assert isinstance(add, Tool)
    assert add.name == "add"
    assert add.description == "Adds two numbers."


def test_tool_decorator_infers_json_schema():
    @tool()
    def greet(name: str, loud: bool = False) -> str:
        return f"hi {name}"

    schema = greet.to_schema()
    assert schema["name"] == "greet"
    assert schema["parameters"]["properties"]["name"] == {"type": "string"}
    assert schema["parameters"]["properties"]["loud"] == {"type": "boolean"}
    assert schema["parameters"]["required"] == ["name"]


def test_tool_run_sync():
    def ping() -> str:
        return "pong"

    t = Tool(name="ping", description="pings", func=ping)
    assert t.run() == "pong"


async def test_tool_arun_wraps_sync_func():
    def ping() -> str:
        return "pong"

    t = Tool(name="ping", description="pings", func=ping)
    assert await t.arun() == "pong"


async def test_tool_arun_native_async():
    async def ping() -> str:
        return "pong-async"

    t = Tool(name="ping", description="pings", func=ping)
    assert await t.arun() == "pong-async"
