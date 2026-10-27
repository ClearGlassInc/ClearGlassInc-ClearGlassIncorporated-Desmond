# ClearGlassInc Agent SDK

A clean, modular Python framework for building tool-using LLM agents:
instructions + state + tool-calling (`Agent`), schema-described function
tools (`Tool`), short/long-term context (`Memory`), pluggable validation
(`Guardrails`), and provider-agnostic execution with sync/async/streaming
support (`Runner` + `LLMClient` adapters).

It ships with zero hard dependencies — provider SDKs (`openai`, `anthropic`)
and HTTP-based connectors (`httpx`) are optional extras, so the core package
installs and runs anywhere.

## Install

```bash
pip install -e .                 # core SDK only
pip install -e ".[openai]"       # + OpenAI client
pip install -e ".[anthropic]"    # + Anthropic client
pip install -e ".[http]"         # + GitHub/Slack/Outlook connectors
pip install -e ".[all]"          # everything
pip install -e ".[dev]"          # + pytest/ruff for development
```

## Quickstart

```python
from clearglassinc_sdk import Agent, Runner, tool
from clearglassinc_sdk.clients.openai_client import OpenAIClient

@tool(description="Adds two numbers")
def add(a: int, b: int) -> int:
    return a + b

agent = Agent(
    name="ClearGlassInc Agent",
    instructions="You are a high-performance, futuristic automation agent.",
)
agent.add_tool(add)

runner = Runner(agent, OpenAIClient(model="gpt-4o-mini"))
result = runner.run("What is 21 plus 21?")
print(result.output)
```

Swap `OpenAIClient` for `AnthropicClient` (`clearglassinc_sdk.clients.anthropic_client`)
to change providers — the `Agent`/`Runner`/`Tool` code above doesn't change.

Run the bundled examples (no API key required — they use a scripted
`FakeLLMClient`):

```bash
python examples/hello_agent.py
python examples/streaming_agent.py
```

## Components

| Module | Purpose |
|---|---|
| `agent.py` | `Agent` — instructions, tools, guardrails, memory, model config |
| `tools.py` | `Tool` / `@tool` — wrap functions with JSON-schema function-calling metadata |
| `memory.py` | `Memory` — bounded short-term history + pluggable `LongTermStore` |
| `guardrails.py` | `Guardrail` protocol + built-ins (`MaxLengthGuardrail`, `RegexBlocklistGuardrail`, `RequiredKeywordsGuardrail`) |
| `runner.py` | `Runner` — drives the tool-calling loop; sync/async, streaming/non-streaming |
| `clients/base.py` | `LLMClient` — provider-agnostic contract (`complete`/`acomplete`/`stream`/`astream`) |
| `clients/openai_client.py` | OpenAI Chat Completions adapter |
| `clients/anthropic_client.py` | Anthropic Messages adapter |
| `connectors/` | `GitHubConnector`, `SlackConnector`, `OutlookConnector` — external systems as `Tool` lists |
| `testing.py` | `FakeLLMClient` — scripted, offline LLM double for tests and examples |
| `cli.py` | `clearglassinc chat` / `clearglassinc version` |

## Streaming

```python
for chunk in runner.run_stream("Summarize the last deploy."):
    print(chunk.delta, end="", flush=True)
```

`arun_stream` is the async equivalent. Adapters that don't implement true
token streaming fall back to a single chunk carrying the full response, so
calling code never has to special-case providers.

## Guardrails

```python
from clearglassinc_sdk.guardrails import MaxLengthGuardrail, RegexBlocklistGuardrail

agent.output_guardrails = [
    MaxLengthGuardrail(max_chars=2000),
    RegexBlocklistGuardrail(patterns=[r"sk-[A-Za-z0-9]{20,}"]),  # e.g. leaked API keys
]
```

A failing guardrail raises `GuardrailViolation` from `Runner.run`/`arun` —
catch it at the call site to show a safe fallback message.

## Connectors

```python
from clearglassinc_sdk.connectors import GitHubConnector

github = GitHubConnector(token=os.environ["GITHUB_TOKEN"])
agent.add_tools(github.as_tools())
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

All tests run against `FakeLLMClient` — no network access or API keys needed.

## CLI

```bash
export CLEARGLASS_PROVIDER=openai   # or anthropic; defaults to an offline fake client
export OPENAI_API_KEY=sk-...
clearglassinc chat
```

## How to run agents

One command runs one governed mission across three agents and exits non-zero
if anything is unverified. It needs no credential and no network:

```bash
cd clearglassinc_sdk
PYTHONPATH=. python3 -m clearglassinc_sdk.cli smoke          # human-readable
PYTHONPATH=. python3 -m clearglassinc_sdk.cli smoke --json   # machine-readable
```

Three roles, three separate `Agent`s, so three separate `Memory` objects. No
role ever sees another's transcript:

| Role | Model | Does |
|------|-------|------|
| `PLANNER` | `claude-opus-5` | Writes a three-step plan |
| `WORKER` | `claude-sonnet-5` | Globs the repo via its one tool, reports paths |
| `CRITIC` | `claude-sonnet-5` | Stats each claimed path, marks Confirmed / Unconfirmed |

The paths and the verdict come from real filesystem calls, not from the model,
so the offline provider cannot fake a pass. To see a failure reported rather
than assumed, add `--inject-bogus`: the critic marks the planted path
`Unconfirmed` and the command exits 1.

Set `CLEARGLASS_PROVIDER=anthropic` plus `ANTHROPIC_API_KEY` to run the same
mission against a live model. A missing package or key prints one line and
exits 2 rather than a traceback. Exit codes: `0` verified, `1` a claim failed
verification, `2` the provider is not configured.
