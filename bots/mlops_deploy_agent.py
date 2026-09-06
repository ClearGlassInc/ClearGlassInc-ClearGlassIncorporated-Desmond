# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Deterministic MLOps deploy-agent primitives used by CI tests.

This module is intentionally dependency-free. It models a signed model/image
promotion pipeline with policy enforcement, canary rollout, rollback, and a
manifest chain hash.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any

_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def _require_sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a sha256 hex digest")
    return value.lower()


@dataclass(frozen=True)
class ModelRef:
    registry: str
    name: str
    version: str
    digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "digest", _require_sha256(self.digest, "digest"))


@dataclass(frozen=True)
class Target:
    runtime: str
    cluster: str
    namespace: str
    strategy: str
    canary_steps: tuple[int, ...] = (100,)

    def __post_init__(self) -> None:
        if not self.canary_steps:
            raise ValueError("canary_steps must not be empty")
        steps = tuple(int(step) for step in self.canary_steps)
        if any(step < 0 or step > 100 for step in steps):
            raise ValueError("canary_steps must be between 0 and 100")
        if list(steps) != sorted(steps):
            raise ValueError("canary_steps must be ascending")
        object.__setattr__(self, "canary_steps", steps)


@dataclass(frozen=True)
class Policy:
    max_p95_ms: int
    cost_ceiling_usd_per_1k: float
    max_error_rate: float = 0.01

    def __post_init__(self) -> None:
        if self.max_p95_ms <= 0:
            raise ValueError("max_p95_ms must be positive")
        if self.cost_ceiling_usd_per_1k < 0:
            raise ValueError("cost_ceiling_usd_per_1k must be non-negative")
        if not 0 <= self.max_error_rate <= 1:
            raise ValueError("max_error_rate must be between 0 and 1")


@dataclass(frozen=True)
class DeployPlan:
    plan_id: str
    model: ModelRef
    target: Target
    policy: Policy
    secrets_ref: str
    image_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "image_digest", _require_sha256(self.image_digest, "image_digest"))


@dataclass(frozen=True)
class DeployManifest:
    plan_id: str
    model_digest: str
    image_digest: str
    signed: bool
    stages: tuple[str, ...]
    chain_hash: str


class PolicyViolation(Exception):
    """Raised when a deployment plan violates policy."""


class StageFailure(Exception):
    """Raised when a pipeline stage fails."""

    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(f"{stage}: {reason}")
        self.stage = stage
        self.reason = reason


@dataclass
class InMemoryRegistry:
    digests: dict[tuple[str, str], str] = field(default_factory=dict)
    signed: set[str] = field(default_factory=set)

    def register(self, name: str, version: str, digest: str, *, signed: bool = False) -> None:
        digest = _require_sha256(digest, "digest")
        self.digests[(name, version)] = digest
        if signed:
            self.signed.add(digest)

    def resolve(self, model: ModelRef) -> str:
        return self.digests.get((model.name, model.version), "")

    def is_signed(self, digest: str) -> bool:
        return digest.lower() in self.signed


@dataclass
class InMemorySecrets:
    store: dict[str, dict[str, str]] = field(default_factory=dict)

    def get(self, ref: str) -> dict[str, str]:
        if ref not in self.store:
            raise KeyError(ref)
        return self.store[ref]


@dataclass
class InMemoryRuntime:
    canary_history: list[tuple[str, int]] = field(default_factory=list)
    rolled_back: set[str] = field(default_factory=set)
    deployments: dict[str, int] = field(default_factory=dict)

    def deploy_canary(self, plan_id: str, weight: int) -> None:
        self.canary_history.append((plan_id, weight))
        self.deployments[plan_id] = weight

    def rollback(self, plan_id: str) -> None:
        self.rolled_back.add(plan_id)
        self.deployments[plan_id] = 0


@dataclass
class InMemoryCI:
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit_billing_event(self, event: dict[str, Any]) -> None:
        self.events.append(dict(event))


@dataclass
class PolicyEngine:
    registry: InMemoryRegistry

    def evaluate(self, plan: DeployPlan) -> list[str]:
        violations: list[str] = []
        if not self.registry.is_signed(plan.model.digest):
            violations.append("model digest is not signed")
        if not self.registry.is_signed(plan.image_digest):
            violations.append("image digest is not signed")
        return violations

    def enforce(self, plan: DeployPlan) -> None:
        violations = self.evaluate(plan)
        if violations:
            raise PolicyViolation("; ".join(violations))


@dataclass
class Supervisor:
    registry: InMemoryRegistry
    runtime: InMemoryRuntime
    secrets: InMemorySecrets
    ci: InMemoryCI

    def run(self, plan: DeployPlan) -> DeployManifest:
        stages: list[str] = []

        def stage(name: str) -> None:
            stages.append(name)

        try:
            stage("intake")

            stage("resolve")
            resolved = self.registry.resolve(plan.model)
            if resolved != plan.model.digest:
                raise StageFailure("resolve", "model digest mismatch")

            stage("secrets")
            self.secrets.get(plan.secrets_ref)

            stage("policy")
            try:
                PolicyEngine(self.registry).enforce(plan)
            except PolicyViolation as exc:
                raise StageFailure("policy", str(exc)) from exc

            stage("deploy")
            for weight in plan.target.canary_steps:
                self.runtime.deploy_canary(plan.plan_id, weight)

            stage("verify")
            metrics = self._metrics_for(plan)
            if metrics["p95_ms"] > plan.policy.max_p95_ms:
                raise StageFailure("verify", "p95 latency exceeds SLO")
            if metrics["error_rate"] > plan.policy.max_error_rate:
                raise StageFailure("verify", "error rate exceeds SLO")
            if metrics["cost_usd_per_1k"] > plan.policy.cost_ceiling_usd_per_1k:
                raise StageFailure("verify", "cost exceeds ceiling")

            stage("promote")
            stage("monetize")
            self.ci.emit_billing_event(
                {
                    "plan_id": plan.plan_id,
                    "model": plan.model.name,
                    "version": plan.model.version,
                    "target": plan.target.cluster,
                }
            )
            return self._manifest(plan, tuple(stages))
        except StageFailure:
            self.runtime.rollback(plan.plan_id)
            raise
        except Exception as exc:
            self.runtime.rollback(plan.plan_id)
            current = stages[-1] if stages else "intake"
            raise StageFailure(current, str(exc)) from exc

    @staticmethod
    def _metrics_for(plan: DeployPlan) -> dict[str, float]:
        return {
            "p95_ms": 50.0,
            "error_rate": 0.001,
            "cost_usd_per_1k": 0.25,
        }

    @staticmethod
    def _manifest(plan: DeployPlan, stages: tuple[str, ...]) -> DeployManifest:
        payload = {
            "plan_id": plan.plan_id,
            "model_digest": plan.model.digest,
            "image_digest": plan.image_digest,
            "target": {
                "runtime": plan.target.runtime,
                "cluster": plan.target.cluster,
                "namespace": plan.target.namespace,
                "strategy": plan.target.strategy,
                "canary_steps": list(plan.target.canary_steps),
            },
            "stages": list(stages),
        }
        chain_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return DeployManifest(
            plan_id=plan.plan_id,
            model_digest=plan.model.digest,
            image_digest=plan.image_digest,
            signed=True,
            stages=stages,
            chain_hash=chain_hash,
        )
