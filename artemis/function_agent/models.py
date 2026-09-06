# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Typed contracts for the Artemis Function Agent."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    """Operational risk attached to a registered capability."""

    SAFE = "safe"
    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"
    FINANCIAL = "financial"


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    APPROVAL_REQUIRED = "approval_required"


class CapabilitySpec(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z0-9_.-]+$")
    description: str
    risk: RiskLevel = RiskLevel.SAFE
    input_schema: dict[str, Any] = Field(default_factory=dict)
    tags: set[str] = Field(default_factory=set)
    timeout_seconds: float = Field(default=30.0, gt=0, le=900)
    idempotent: bool = False


class ExecutionContext(BaseModel):
    actor: str = "system"
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    roles: set[str] = Field(default_factory=set)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionRequest(BaseModel):
    capability: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    approval_token: str | None = None
    context: ExecutionContext = Field(default_factory=ExecutionContext)


class ExecutionResult(BaseModel):
    request_id: str
    capability: str
    status: ExecutionStatus
    output: Any = None
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float = 0.0
    audit_hash: str | None = None
    approval_id: str | None = None


class ApprovalChallenge(BaseModel):
    approval_id: str = Field(default_factory=lambda: uuid4().hex)
    capability: str
    arguments_digest: str
    actor: str
    reason: str
    expires_at: datetime


class ApprovalGrant(BaseModel):
    approval_id: str
    token: str
    expires_at: datetime


class BatchExecutionRequest(BaseModel):
    requests: list[ExecutionRequest] = Field(min_length=1, max_length=100)
    max_concurrency: int = Field(default=4, ge=1, le=32)
    fail_fast: bool = False
