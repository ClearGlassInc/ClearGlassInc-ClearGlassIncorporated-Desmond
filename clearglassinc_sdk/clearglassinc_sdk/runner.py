"""The `Runner`: drives an `Agent` through an LLM client, dispatching tool
calls and enforcing guardrails until a final answer is produced."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

from clearglassinc_sdk.agent import Agent
from clearglassinc_sdk.clients.base import CompletionResult, LLMClient, StreamChunk, ToolCall
from clearglassinc_sdk.exceptions import GuardrailViolation, MaxStepsExceeded, ToolExecutionError
from clearglassinc_sdk.guardrails import run_guardrails
from clearglassinc_sdk.memory import Message


@dataclass
class RunResult:
    output: str
    messages: list[Message] = field(default_factory=list)
    steps: int = 0


def _tool_calls_to_dicts(tool_calls: list[ToolCall]) -> list[dict[str, Any]]:
    return [
        {
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
        }
        for call in tool_calls
    ]


class Runner:
    """Executes an `Agent`'s tool-calling loop against an `LLMClient`."""

    def __init__(self, agent: Agent, llm_client: LLMClient):
        self.agent = agent
        self.llm_client = llm_client

    def _check_input(self, prompt: str) -> None:
        result = run_guardrails(self.agent.input_guardrails, prompt)
        if not result.passed:
            raise GuardrailViolation("input", result.reason)

    def _check_output(self, content: str) -> None:
        result = run_guardrails(self.agent.output_guardrails, content)
        if not result.passed:
            raise GuardrailViolation("output", result.reason)

    def _execute_tool_calls(self, tool_calls: list[ToolCall]) -> None:
        for call in tool_calls:
            tool = self.agent.get_tool(call.name)
            if tool is None:
                self.agent.memory.add_tool_result(
                    call.id, call.name, f"error: no such tool '{call.name}'"
                )
                continue
            try:
                output = tool.run(**call.arguments)
            except Exception as exc:
                raise ToolExecutionError(call.name, exc) from exc
            self.agent.memory.add_tool_result(call.id, call.name, str(output))

    async def _aexecute_tool_calls(self, tool_calls: list[ToolCall]) -> None:
        for call in tool_calls:
            tool = self.agent.get_tool(call.name)
            if tool is None:
                self.agent.memory.add_tool_result(
                    call.id, call.name, f"error: no such tool '{call.name}'"
                )
                continue
            try:
                output = await tool.arun(**call.arguments)
            except Exception as exc:
                raise ToolExecutionError(call.name, exc) from exc
            self.agent.memory.add_tool_result(call.id, call.name, str(output))

    def run(self, prompt: str) -> RunResult:
        """Run the agent to completion (synchronous, non-streaming)."""
        self._check_input(prompt)
        self.agent.memory.add_user(prompt)

        for step in range(1, self.agent.max_steps + 1):
            result: CompletionResult = self.llm_client.complete(
                self.agent.memory.history(),
                system=self.agent.instructions,
                tools=self.agent.tool_schemas() or None,
                model=self.agent.model,
                temperature=self.agent.temperature,
            )

            if result.has_tool_calls:
                self.agent.memory.add_assistant(
                    result.content, tool_calls=_tool_calls_to_dicts(result.tool_calls)
                )
                self._execute_tool_calls(result.tool_calls)
                continue

            self._check_output(result.content)
            self.agent.memory.add_assistant(result.content)
            return RunResult(output=result.content, messages=self.agent.memory.history(), steps=step)

        raise MaxStepsExceeded(self.agent.max_steps)

    async def arun(self, prompt: str) -> RunResult:
        """Run the agent to completion (async, non-streaming)."""
        self._check_input(prompt)
        self.agent.memory.add_user(prompt)

        for step in range(1, self.agent.max_steps + 1):
            result = await self.llm_client.acomplete(
                self.agent.memory.history(),
                system=self.agent.instructions,
                tools=self.agent.tool_schemas() or None,
                model=self.agent.model,
                temperature=self.agent.temperature,
            )

            if result.has_tool_calls:
                self.agent.memory.add_assistant(
                    result.content, tool_calls=_tool_calls_to_dicts(result.tool_calls)
                )
                await self._aexecute_tool_calls(result.tool_calls)
                continue

            self._check_output(result.content)
            self.agent.memory.add_assistant(result.content)
            return RunResult(output=result.content, messages=self.agent.memory.history(), steps=step)

        raise MaxStepsExceeded(self.agent.max_steps)

    def run_stream(self, prompt: str) -> Iterator[StreamChunk]:
        """Run the agent, yielding `StreamChunk`s as each step produces them.
        Tool-call steps are yielded (empty-delta, tool_calls populated) then
        executed before continuing; the final text-only step streams its
        content incrementally if the underlying client supports it."""
        self._check_input(prompt)
        self.agent.memory.add_user(prompt)

        for step in range(1, self.agent.max_steps + 1):
            content = ""
            tool_calls: list[ToolCall] = []
            for chunk in self.llm_client.stream(
                self.agent.memory.history(),
                system=self.agent.instructions,
                tools=self.agent.tool_schemas() or None,
                model=self.agent.model,
                temperature=self.agent.temperature,
            ):
                content += chunk.delta
                if chunk.tool_calls:
                    tool_calls = chunk.tool_calls
                yield chunk

            if tool_calls:
                self.agent.memory.add_assistant(content, tool_calls=_tool_calls_to_dicts(tool_calls))
                self._execute_tool_calls(tool_calls)
                continue

            self._check_output(content)
            self.agent.memory.add_assistant(content)
            return

        raise MaxStepsExceeded(self.agent.max_steps)

    async def arun_stream(self, prompt: str) -> AsyncIterator[StreamChunk]:
        """Async variant of `run_stream`."""
        self._check_input(prompt)
        self.agent.memory.add_user(prompt)

        for step in range(1, self.agent.max_steps + 1):
            content = ""
            tool_calls: list[ToolCall] = []
            async for chunk in self.llm_client.astream(
                self.agent.memory.history(),
                system=self.agent.instructions,
                tools=self.agent.tool_schemas() or None,
                model=self.agent.model,
                temperature=self.agent.temperature,
            ):
                content += chunk.delta
                if chunk.tool_calls:
                    tool_calls = chunk.tool_calls
                yield chunk

            if tool_calls:
                self.agent.memory.add_assistant(content, tool_calls=_tool_calls_to_dicts(tool_calls))
                await self._aexecute_tool_calls(tool_calls)
                continue

            self._check_output(content)
            self.agent.memory.add_assistant(content)
            return

        raise MaxStepsExceeded(self.agent.max_steps)
