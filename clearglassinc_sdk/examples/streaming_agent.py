"""Streaming example: consume `StreamChunk`s as an agent responds.

    python examples/streaming_agent.py

Swap `FakeLLMClient` for `OpenAIClient`/`AnthropicClient` to stream real
model output — the `Runner.run_stream` / `arun_stream` interface is identical.
"""

from clearglassinc_sdk import Agent, Runner
from clearglassinc_sdk.testing import FakeLLMClient, text_response


def main() -> None:
    agent = Agent(
        name="ClearGlassInc Streaming Agent",
        instructions="You are a concise, futuristic automation agent.",
    )
    client = FakeLLMClient(responses=[text_response("Streaming responses, one chunk at a time.")])
    runner = Runner(agent, client)

    print("> ", end="", flush=True)
    for chunk in runner.run_stream("Say something streaming-friendly."):
        print(chunk.delta, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
