# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Execution engine for the Artemis Function Agent."""
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .audit import HashChainAuditLog
from .guardrails import GuardrailPipeline
from .memory import SQLiteMemory
from .models import (
    BatchExecutionRequest,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    PolicyDecision,
)
from .policy import AgentPolicy, ApprovalManager, arguments_digest
from .registry import CapabilityRegistry


class FunctionAgentSettings(BaseModel):
    state_dir: Path = Path(".artemis/function-agent")
    max_output_bytes: int = Field(default=1_000_000, ge=1_024, le=10_000_000)
    idempotency_ttl_seconds: int = Field(default=3600, ge=0, le=86_400)
    max_retries: int = Field(default=1, ge=0, le=5)
    circuit_failure_threshold: int = Field(default=5, ge=1, le=100)
    circuit_window_seconds: int = Field(default=60, ge=1, le=3600)
    circuit_reset_seconds: int = Field(default=120, ge=1, le=86_400)


class CircuitOpenError(RuntimeError):
    pass


class FunctionAgent:
    """Policy-controlled execution plane for registered Python capabilities."""

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        policy: AgentPolicy | None = None,
        approvals: ApprovalManager | None = None,
        guardrails: GuardrailPipeline | None = None,
        settings: FunctionAgentSettings | None = None,
    ) -> None:
        self.registry = registry or CapabilityRegistry()
        self.policy = policy or AgentPolicy()
        self.settings = settings or FunctionAgentSettings()
        self.settings.state_dir.mkdir(parents=True, exist_ok=True)
        self.approvals = approvals or ApprovalManager()
        self.guardrails = guardrails or GuardrailPipeline()
        self.memory = SQLiteMemory(self.settings.state_dir / "memory.sqlite3")
        self.audit = HashChainAuditLog(self.settings.state_dir / "audit.jsonl")
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._circuit_opened_at: dict[str, float] = {}

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        started_wall = datetime.now(UTC)
        started_perf = time.perf_counter()
        try:
            registered = self.registry.get(request.capability)
        except KeyError as exc:
            return self._finalize(
                request,
                ExecutionStatus.FAILED,
                started_wall,
                started_perf,
                error=str(exc),
            )

        try:
            await self.guardrails.validate_input(request)
        except Exception as exc:  # noqa: BLE001 - guardrail failures are contained
            return self._finalize(
                request,
                ExecutionStatus.DENIED,
                started_wall,
                started_perf,
                error=f"{type(exc).__name__}: {exc}",
            )

        policy_result = self.policy.evaluate(registered.spec, request.context)
        if policy_result.decision is PolicyDecision.DENY:
            return self._finalize(
                request,
                ExecutionStatus.DENIED,
                started_wall,
                started_perf,
                error=policy_result.reason,
            )

        if policy_result.decision is PolicyDecision.REQUIRE_APPROVAL:
            approved = bool(request.approval_token) and self.approvals.validate_and_consume(
                request.approval_token,
                request.capability,
                request.arguments,
                request.context,
            )
            if not approved:
                challenge = self.approvals.challenge(
                    request.capability,
                    request.arguments,
                    request.context,
                    policy_result.reason,
                )
                return self._finalize(
                    request,
                    ExecutionStatus.APPROVAL_REQUIRED,
                    started_wall,
                    started_perf,
                    error=policy_result.reason,
                    approval_id=challenge.approval_id,
                )

        cache_key = self._idempotency_key(request)
        if registered.spec.idempotent and self.settings.idempotency_ttl_seconds:
            cached = self.memory.get("idempotency", cache_key)
            if cached is not None:
                return self._finalize(
                    request,
                    ExecutionStatus.SUCCEEDED,
                    started_wall,
                    started_perf,
                    output={"cached": True, "value": cached},
                )

        try:
            self._assert_circuit_closed(request.capability)
            output = await self._invoke_with_retries(registered, request.arguments)
            normalized = self._normalize_output(output)
            await self.guardrails.validate_output(request, normalized)
            self._record_success(request.capability)
            if registered.spec.idempotent and self.settings.idempotency_ttl_seconds:
                self.memory.set(
                    "idempotency",
                    cache_key,
                    normalized,
                    ttl_seconds=self.settings.idempotency_ttl_seconds,
                )
            return self._finalize(
                request,
                ExecutionStatus.SUCCEEDED,
                started_wall,
                started_perf,
                output=normalized,
            )
        except Exception as exc:  # noqa: BLE001 - capability boundary must be contained
            self._record_failure(request.capability)
            return self._finalize(
                request,
                ExecutionStatus.FAILED,
                started_wall,
                started_perf,
                error=f"{type(exc).__name__}: {exc}",
            )

    async def execute_batch(self, batch: BatchExecutionRequest) -> list[ExecutionResult]:
        if batch.fail_fast:
            results: list[ExecutionResult] = []
            for request in batch.requests:
                result = await self.execute(request)
                results.append(result)
                if result.status is not ExecutionStatus.SUCCEEDED:
                    break
            return results

        semaphore = asyncio.Semaphore(batch.max_concurrency)

        async def bounded(request: ExecutionRequest) -> ExecutionResult:
            async with semaphore:
                return await self.execute(request)

        return list(await asyncio.gather(*(bounded(item) for item in batch.requests)))

    async def _invoke_with_retries(self, registered: Any, arguments: dict[str, Any]) -> Any:
        attempts = self.settings.max_retries + 1 if registered.spec.idempotent else 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                async with asyncio.timeout(registered.spec.timeout_seconds):
                    return await registered.invoke(arguments)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(min(0.25 * (2**attempt), 2.0))
        assert last_error is not None
        raise last_error

    def _normalize_output(self, output: Any) -> Any:
        payload = json.dumps(output, sort_keys=True, default=str).encode("utf-8")
        if len(payload) > self.settings.max_output_bytes:
            raise ValueError(
                f"Capability output exceeded {self.settings.max_output_bytes} bytes"
            )
        return json.loads(payload)

    def _assert_circuit_closed(self, capability: str) -> None:
        opened_at = self._circuit_opened_at.get(capability)
        if opened_at is None:
            return
        if time.monotonic() - opened_at >= self.settings.circuit_reset_seconds:
            self._circuit_opened_at.pop(capability, None)
            self._failures[capability].clear()
            return
        raise CircuitOpenError(f"Circuit open for capability: {capability}")

    def _record_failure(self, capability: str) -> None:
        now = time.monotonic()
        failures = self._failures[capability]
        failures.append(now)
        cutoff = now - self.settings.circuit_window_seconds
        while failures and failures[0] < cutoff:
            failures.popleft()
        if len(failures) >= self.settings.circuit_failure_threshold:
            self._circuit_opened_at[capability] = now

    def _record_success(self, capability: str) -> None:
        self._failures[capability].clear()
        self._circuit_opened_at.pop(capability, None)

    @staticmethod
    def _idempotency_key(request: ExecutionRequest) -> str:
        return ":".join(
            (request.context.actor, request.capability, arguments_digest(request.arguments))
        )

    def _finalize(
        self,
        request: ExecutionRequest,
        status: ExecutionStatus,
        started_wall: datetime,
        started_perf: float,
        *,
        output: Any = None,
        error: str | None = None,
        approval_id: str | None = None,
    ) -> ExecutionResult:
        finished = datetime.now(UTC)
        duration = round((time.perf_counter() - started_perf) * 1000, 3)
        event = {
            "request_id": request.context.request_id,
            "actor": request.context.actor,
            "roles": sorted(request.context.roles),
            "capability": request.capability,
            "arguments_digest": arguments_digest(request.arguments),
            "status": status,
            "error": error,
            "approval_id": approval_id,
            "duration_ms": duration,
        }
        audit_hash = self.audit.append(event)
        return ExecutionResult(
            request_id=request.context.request_id,
            capability=request.capability,
            status=status,
            output=output,
            error=error,
            started_at=started_wall,
            finished_at=finished,
            duration_ms=duration,
            audit_hash=audit_hash,
            approval_id=approval_id,
        )
