# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Typed schema for DeployPlan and stage results.

Uses stdlib dataclasses with strict validation in __post_init__ so the agent
package has zero runtime dependencies. Digests must be SHA256 hex strings.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_VALID_REGISTRIES = ("mlflow", "sagemaker")
_VALID_RUNTIMES = ("kserve", "sagemaker", "ecs")
_VALID_STRATEGIES = ("bluegreen", "canary")


def _require_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ValueError(f"{field_name} must be a 64-char lowercase SHA256 hex digest")


def _require_in(value: str, choices: Iterable[str], field_name: str) -> None:
    if value not in choices:
        raise ValueError(f"{field_name} must be one of {tuple(choices)}, got {value!r}")


@dataclass(frozen=True)
class ModelRef:
    registry: str
    name: str
    version: str
    digest: str

    def __post_init__(self) -> None:
        _require_in(self.registry, _VALID_REGISTRIES, "model.registry")
        if not self.name:
            raise ValueError("model.name is required")
        if not self.version:
            raise ValueError("model.version is required")
        _require_sha256(self.digest, "model.digest")


@dataclass(frozen=True)
class Target:
    runtime: str
    cluster: str
    namespace: str
    strategy: str
    canary_steps: tuple[int, ...] = (5, 50, 100)

    def __post_init__(self) -> None:
        _require_in(self.runtime, _VALID_RUNTIMES, "target.runtime")
        _require_in(self.strategy, _VALID_STRATEGIES, "target.strategy")
        if not self.cluster:
            raise ValueError("target.cluster is required")
        if not self.namespace:
            raise ValueError("target.namespace is required")
        if not self.canary_steps or any(s <= 0 or s > 100 for s in self.canary_steps):
            raise ValueError("target.canary_steps must be non-empty in (0, 100]")
        if list(self.canary_steps) != sorted(self.canary_steps):
            raise ValueError("target.canary_steps must be ascending")


@dataclass(frozen=True)
class Policy:
    max_p95_ms: int
    cost_ceiling_usd_per_1k: float
    max_error_rate: float = 0.01
    require_signed: bool = True

    def __post_init__(self) -> None:
        if self.max_p95_ms <= 0:
            raise ValueError("policy.max_p95_ms must be positive")
        if not (0.0 <= self.max_error_rate <= 1.0):
            raise ValueError("policy.max_error_rate must be in [0, 1]")
        if self.cost_ceiling_usd_per_1k <= 0:
            raise ValueError("policy.cost_ceiling_usd_per_1k must be positive")


@dataclass(frozen=True)
class DeployPlan:
    plan_id: str
    model: ModelRef
    target: Target
    policy: Policy
    secrets_ref: str
    image_digest: str
    rollback_on_fail: bool = True

    def __post_init__(self) -> None:
        if not self.plan_id:
            raise ValueError("plan_id is required")
        if not self.secrets_ref:
            raise ValueError("secrets_ref is required")
        _require_sha256(self.image_digest, "image_digest")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StageResult:
    stage: str
    status: str  # "OK" | "NEEDS_REPAIR" | "FAILED"
    data: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "OK"


@dataclass(frozen=True)
class AuditManifest:
    plan_id: str
    image_digest: str
    model_digest: str
    stages: tuple[str, ...]
    chain_hash: str
    signed: bool
