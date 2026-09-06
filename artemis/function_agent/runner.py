# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Async-first model runner with tool loops and provider-native streaming."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from .agent import FunctionAgent
from .llm_clients import (
    ChatMessage,
    LLMClient,
    LLMResponse,
    LLMStreamEvent,
    MessageRole,
    ToolCall,
)
from .models import ExecutionContext, ExecutionRequest, ExecutionResult, ExecutionStatus


class RunStatus(StrEnum):
    COMPLETED = "completed"
    APPROVAL_REQUIRED = "approval_required"
    FAILED = "failed"
    MAX_TURNS = "max_turns"


class RunnerSettings(BaseModel):
    system_prompt: str = (
        "You are Artemis, the ClearGlassInc function agent. Use registered tools only when "
        "needed, never fabricate tool results, and stop when approval is required."
    )
    max_turns: int = Field(default=12, ge=1, le=100)
    parallel_tool_calls: bool = True


class RunResult(BaseModel):
    status: RunStatus
    text: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
    tool_results: list[ExecutionResult] = Field(default_factory=list)
    pending_approvals: list[str] = Field(default_factory=list)
    turns: int = 0
    error: str | None = None


class AgentRunner:
    """Coordinates an LLM client with deterministic FunctionAgent execution."""

    def __init__(
        self,
        agent: FunctionAgent,
        llm_client: LLMClient,
        settings: RunnerSettings | None = None,
    ) -> None:
        self.agent = agent
        self.llm_client = llm_client
        self.settings = settings or RunnerSettings()

    async def run(
        self,
        prompt: str,
        *,
        context: ExecutionContext | None = None,
        history: list[ChatMessage] | None = None,
        approval_tokens: dict[str, str] | None = None,
    ) -> RunResult:
        execution_context = context or ExecutionContext(actor="runner")
        messages = self._initial_messages(prompt, history)
        tool_results: list[ExecutionResult] = []
        approvals: list[str] = []

        for turn in range(1, self.settings.max_turns + 1):
            try:
                response = await self.llm_client.complete(messages, self._tool_schemas())
            except Exception as exc:  # noqa: BLE001 - provider boundary
                return RunResult(
                    status=RunStatus.FAILED,
                    messages=messages,
                    tool_results=tool_results,
                    turns=turn,
                    error=f"{type(exc).__name__}: {exc}",
                )

            messages.append(self._assistant_message(response))
            if not response.tool_calls:
                return RunResult(
                    status=RunStatus.COMPLETED,
                    text=response.text,
                    messages=messages,
                    tool_results=tool_results,
                    turns=turn,
                )

            results = await self._execute_tool_calls(
                response.tool_calls,
                execution_context,
                approval_tokens or {},
            )
            tool_results.extend(results)
            self._append_tool_messages(messages, response.tool_calls, results)
            approvals.extend(
                result.approval_id
                for result in results
                if result.status is ExecutionStatus.APPROVAL_REQUIRED and result.approval_id
            )
            if approvals:
                return RunResult(
                    status=RunStatus.APPROVAL_REQUIRED,
                    text=response.text,
                    messages=messages,
                    tool_results=tool_results,
                    pending_approvals=approvals,
                    turns=turn,
                )

        return RunResult(
            status=RunStatus.MAX_TURNS,
            messages=messages,
            tool_results=tool_results,
            turns=self.settings.max_turns,
            error="Maximum model/tool turns reached",
        )

    async def stream(
        self,
        prompt: str,
        *,
        context: ExecutionContext | None = None,
        history: list[ChatMessage] | None = None,
        approval_tokens: dict[str, str] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        """Stream model events while preserving the full multi-turn tool loop."""
        execution_context = context or ExecutionContext(actor="runner")
        messages = self._initial_messages(prompt, history)

        for turn in range(1, self.settings.max_turns + 1):
            text_parts: list[str] = []
            tool_calls: list[ToolCall] = []
            final_response: LLMResponse | None = None

            async for event in self.llm_client.stream(messages, self._tool_schemas()):
                if event.text_delta:
                    text_parts.append(event.text_delta)
                if event.tool_call is not None:
                    tool_calls.append(event.tool_call)
                if event.response is not None:
                    final_response = event.response
                yield event

            response = final_response or LLMResponse(text="".join(text_parts))
            if not tool_calls:
                tool_calls = list(response.tool_calls)
            if tool_calls != response.tool_calls:
                response = response.model_copy(update={"tool_calls": tool_calls})

            messages.append(self._assistant_message(response))
            if not tool_calls:
                yield LLMStreamEvent(
                    type="runner.completed",
                    response=response,
                    metadata={"turn": turn},
                )
                return

            results = await self._execute_tool_calls(
                tool_calls,
                execution_context,
                approval_tokens or {},
            )
            self._append_tool_messages(messages, tool_calls, results)
            for call, result in zip(tool_calls, results, strict=True):
                yield LLMStreamEvent(
                    type="runner.tool_result",
                    tool_call=call,
                    metadata={"turn": turn, "result": result.model_dump(mode="json")},
                )
            if any(result.status is ExecutionStatus.APPROVAL_REQUIRED for result in results):
                yield LLMStreamEvent(
                    type="runner.approval_required",
                    metadata={
                        "turn": turn,
                        "approval_ids": [
                            result.approval_id
                            for result in results
                            if result.approval_id is not None
                        ],
                    },
                )
                return

        yield LLMStreamEvent(
            type="runner.max_turns",
            metadata={"turns": self.settings.max_turns},
        )

    async def _execute_tool_calls(
        self,
        calls: list[ToolCall],
        context: ExecutionContext,
        approval_tokens: dict[str, str],
    ) -> list[ExecutionResult]:
        async def execute(call: ToolCall) -> ExecutionResult:
            call_context = context.model_copy(
                update={"request_id": f"{context.request_id}:{call.id}"}
            )
            return await self.agent.execute(
                ExecutionRequest(
                    capability=call.name,
                    arguments=call.arguments,
                    approval_token=approval_tokens.get(call.id) or approval_tokens.get(call.name),
                    context=call_context,
                )
            )

        if self.settings.parallel_tool_calls:
            return list(await asyncio.gather(*(execute(call) for call in calls)))
        results: list[ExecutionResult] = []
        for call in calls:
            results.append(await execute(call))
        return results

    def _tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.input_schema,
                    "strict": True,
                },
            }
            for spec in self.agent.registry.list()
        ]

    def _initial_messages(
        self, prompt: str, history: list[ChatMessage] | None
    ) -> list[ChatMessage]:
        messages = [ChatMessage(role=MessageRole.SYSTEM, content=self.settings.system_prompt)]
        messages.extend(history or [])
        messages.append(ChatMessage(role=MessageRole.USER, content=prompt))
        return messages

    @staticmethod
    def _assistant_message(response: LLMResponse) -> ChatMessage:
        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=response.text,
            metadata={
                "tool_calls": [call.model_dump(mode="json") for call in response.tool_calls],
                "finish_reason": response.finish_reason,
                "usage": response.usage,
            },
        )

    @staticmethod
    def _append_tool_messages(
        messages: list[ChatMessage],
        calls: list[ToolCall],
        results: list[ExecutionResult],
    ) -> None:
        for call, result in zip(calls, results, strict=True):
            messages.append(
                ChatMessage(
                    role=MessageRole.TOOL,
                    name=call.name,
                    tool_call_id=call.id,
                    content=json.dumps(result.model_dump(mode="json"), sort_keys=True),
                )
            )
