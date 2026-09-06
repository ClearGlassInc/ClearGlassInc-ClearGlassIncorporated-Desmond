# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""FastAPI control plane for the Artemis Function Agent."""
from __future__ import annotations

import hmac
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from .models import (
    BatchExecutionRequest,
    CapabilitySpec,
    ExecutionContext,
    ExecutionRequest,
    ExecutionResult,
)
from .runtime import AgentRuntime, build_runtime


class APIExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    approval_token: str | None = None
    request_id: str = Field(default_factory=lambda: uuid4().hex)


class APIBatchExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requests: list[APIExecutionRequest] = Field(min_length=1, max_length=100)
    max_concurrency: int = Field(default=4, ge=1, le=32)
    fail_fast: bool = False


def create_router(runtime: AgentRuntime) -> APIRouter:
    router = APIRouter(prefix="/v1")

    def operator_authenticated(operator_key: str | None) -> bool:
        configured = runtime.settings.operator_key
        if configured is None or operator_key is None:
            return False
        return hmac.compare_digest(configured.get_secret_value(), operator_key)

    def execution_context(
        actor: str | None,
        operator_key: str | None,
        request_id: str,
    ) -> ExecutionContext:
        return ExecutionContext(
            actor=actor or "api-client",
            request_id=request_id,
            roles={"operator"} if operator_authenticated(operator_key) else set(),
            metadata={"transport": "http"},
        )

    @router.get("/capabilities", response_model=list[CapabilitySpec])
    async def list_capabilities() -> list[CapabilitySpec]:
        return runtime.agent.registry.list()

    @router.post("/execute", response_model=ExecutionResult)
    async def execute(
        payload: APIExecutionRequest,
        actor: Annotated[str | None, Header(alias="X-Artemis-Actor")] = None,
        operator_key: Annotated[
            str | None, Header(alias="X-Artemis-Operator-Key")
        ] = None,
    ) -> ExecutionResult:
        return await runtime.agent.execute(
            ExecutionRequest(
                capability=payload.capability,
                arguments=payload.arguments,
                approval_token=payload.approval_token,
                context=execution_context(actor, operator_key, payload.request_id),
            )
        )

    @router.post("/execute/batch", response_model=list[ExecutionResult])
    async def execute_batch(
        payload: APIBatchExecutionRequest,
        actor: Annotated[str | None, Header(alias="X-Artemis-Actor")] = None,
        operator_key: Annotated[
            str | None, Header(alias="X-Artemis-Operator-Key")
        ] = None,
    ) -> list[ExecutionResult]:
        batch = BatchExecutionRequest(
            requests=[
                ExecutionRequest(
                    capability=item.capability,
                    arguments=item.arguments,
                    approval_token=item.approval_token,
                    context=execution_context(actor, operator_key, item.request_id),
                )
                for item in payload.requests
            ],
            max_concurrency=payload.max_concurrency,
            fail_fast=payload.fail_fast,
        )
        return await runtime.agent.execute_batch(batch)

    @router.post("/approvals/{approval_id}/grant")
    async def grant_approval(
        approval_id: str,
        operator_key: Annotated[
            str | None, Header(alias="X-Artemis-Operator-Key")
        ] = None,
    ) -> dict[str, Any]:
        if runtime.settings.operator_key is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Approval grants are disabled until an operator key is configured",
            )
        if not operator_authenticated(operator_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid operator credentials are required",
            )
        try:
            return runtime.agent.approvals.grant(approval_id).model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval challenge not found or expired",
            ) from exc

    @router.get("/audit/verify")
    async def verify_audit() -> dict[str, Any]:
        valid, records = runtime.agent.audit.verify()
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"valid": False, "records_verified": records},
            )
        return {"valid": True, "records_verified": records}

    return router


def create_app(runtime: AgentRuntime | None = None) -> FastAPI:
    active_runtime = runtime or build_runtime()
    app = FastAPI(
        title="ClearGlassInc Artemis Function Agent",
        version="1.0.0",
        description=(
            "Policy-controlled capability execution with approvals, guardrails, memory, "
            "bounded connectors, and tamper-evident auditing."
        ),
    )

    @app.get("/health/live")
    async def health_live() -> dict[str, Any]:
        return {"status": "live"}

    @app.get("/health/ready")
    async def health_ready() -> dict[str, Any]:
        valid, records = active_runtime.agent.audit.verify()
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Audit chain verification failed",
            )
        return {
            "status": "ready",
            "capabilities": len(active_runtime.agent.registry.list()),
            "audit_records": records,
        }

    app.include_router(create_router(active_runtime))
    app.state.artemis_runtime = active_runtime
    return app
