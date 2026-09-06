"""The `Agent`: instructions, tools, memory, and guardrails bundled together.

An `Agent` is a static description of a persona and its capabilities. It does
not itself talk to an LLM — hand it to a `Runner` (paired with an `LLMClient`)
to actually execute turns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from clearglassinc_sdk.guardrails import Guardrail
from clearglassinc_sdk.memory import Memory
from clearglassinc_sdk.tools import Tool


@dataclass
class Agent:
    name: str
    instructions: str
    tools: list[Tool] = field(default_factory=list)
    input_guardrails: list[Guardrail] = field(default_factory=list)
    output_guardrails: list[Guardrail] = field(default_factory=list)
    memory: Memory = field(default_factory=Memory)
    model: str | None = None
    temperature: float = 0.7
    max_steps: int = 10
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_tool(self, tool: Tool) -> None:
        if any(existing.name == tool.name for existing in self.tools):
            raise ValueError(f"a tool named '{tool.name}' is already registered")
        self.tools.append(tool)

    def add_tools(self, tools: list[Tool]) -> None:
        for t in tools:
            self.add_tool(t)

    def get_tool(self, name: str) -> Tool | None:
        return next((t for t in self.tools if t.name == name), None)

    def list_tools(self) -> list[str]:
        return [t.name for t in self.tools]

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [t.to_schema() for t in self.tools]
