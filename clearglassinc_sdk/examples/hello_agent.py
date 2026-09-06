"""Minimal example: an agent with one tool, run against a scripted fake LLM
client so this runs offline with no API key.

    python examples/hello_agent.py
"""

from clearglassinc_sdk import Agent, Runner, tool
from clearglassinc_sdk.testing import FakeLLMClient, text_response, tool_call_response


@tool(description="Returns pong, proving the tool-calling loop works.")
def ping() -> str:
    return "pong"


def main() -> None:
    agent = Agent(
        name="ClearGlassInc Agent",
        instructions="You are a high-performance, futuristic automation agent.",
    )
    agent.add_tool(ping)

    # Script two turns: first the model calls `ping`, then it answers using
    # the tool's result. A real client (OpenAIClient/AnthropicClient) would
    # decide this on its own.
    client = FakeLLMClient(
        responses=[
            tool_call_response(call_id="call_1", tool_name="ping", arguments={}),
            text_response("The ping tool replied: pong"),
        ]
    )

    runner = Runner(agent, client)
    result = runner.run("Call the ping tool and tell me what it returned.")
    print(result.output)
    print(f"(completed in {result.steps} step(s))")


if __name__ == "__main__":
    main()
