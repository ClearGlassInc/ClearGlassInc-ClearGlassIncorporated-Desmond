# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Composable async guardrails for requests, arguments, and outputs."""
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from .models import ExecutionRequest


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    passed: bool
    reason: str = ""
    metadata: dict[str, Any] | None = None


class Guardrail(Protocol):
    name: str

    def validate_input(
        self, request: ExecutionRequest
    ) -> GuardrailResult | Awaitable[GuardrailResult]: ...

    def validate_output(
        self, request: ExecutionRequest, output: Any
    ) -> GuardrailResult | Awaitable[GuardrailResult]: ...


class GuardrailViolation(RuntimeError):
    def __init__(self, phase: str, guardrail: str, reason: str) -> None:
        super().__init__(f"{phase} guardrail '{guardrail}' rejected execution: {reason}")
        self.phase = phase
        self.guardrail = guardrail
        self.reason = reason


class GuardrailPipeline:
    """Runs deterministic guardrails in registration order and fails closed."""

    def __init__(self, guardrails: Sequence[Guardrail] | None = None) -> None:
        self._guardrails = list(guardrails or [])

    def add(self, guardrail: Guardrail) -> None:
        self._guardrails.append(guardrail)

    async def validate_input(self, request: ExecutionRequest) -> None:
        for guardrail in self._guardrails:
            result = await self._resolve(guardrail.validate_input(request))
            if not result.passed:
                raise GuardrailViolation("input", guardrail.name, result.reason)

    async def validate_output(self, request: ExecutionRequest, output: Any) -> None:
        for guardrail in reversed(self._guardrails):
            result = await self._resolve(guardrail.validate_output(request, output))
            if not result.passed:
                raise GuardrailViolation("output", guardrail.name, result.reason)

    @staticmethod
    async def _resolve(
        result: GuardrailResult | Awaitable[GuardrailResult],
    ) -> GuardrailResult:
        resolved = await result if inspect.isawaitable(result) else result
        if not isinstance(resolved, GuardrailResult):
            raise TypeError("Guardrails must return GuardrailResult")
        return resolved


Predicate = Callable[[ExecutionRequest], bool | Awaitable[bool]]
OutputPredicate = Callable[[ExecutionRequest, Any], bool | Awaitable[bool]]


@dataclass(slots=True)
class PredicateGuardrail:
    """Convenience guardrail for application-supplied predicates."""

    name: str
    input_predicate: Predicate | None = None
    output_predicate: OutputPredicate | None = None
    rejection_reason: str = "Rejected by policy predicate"

    async def validate_input(self, request: ExecutionRequest) -> GuardrailResult:
        if self.input_predicate is None:
            return GuardrailResult(True)
        result = self.input_predicate(request)
        passed = await result if inspect.isawaitable(result) else result
        return GuardrailResult(bool(passed), "" if passed else self.rejection_reason)

    async def validate_output(self, request: ExecutionRequest, output: Any) -> GuardrailResult:
        if self.output_predicate is None:
            return GuardrailResult(True)
        result = self.output_predicate(request, output)
        passed = await result if inspect.isawaitable(result) else result
        return GuardrailResult(bool(passed), "" if passed else self.rejection_reason)
