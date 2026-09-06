# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Adapter interfaces for registry, runtime, secrets, and CI.

Real adapters (MLflow, SageMaker, KServe, Vault, GitHub Actions) implement
these protocols. The In-Memory implementations are deterministic doubles used
by tests and dry-run executions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .schema import DeployPlan


class RegistryAdapter(ABC):
    @abstractmethod
    def resolve_digest(self, name: str, version: str) -> str: ...

    @abstractmethod
    def is_signed(self, digest: str) -> bool: ...


class RuntimeAdapter(ABC):
    @abstractmethod
    def provision(self, plan: DeployPlan) -> dict[str, Any]: ...

    @abstractmethod
    def deploy_canary(self, plan: DeployPlan, weight_pct: int) -> dict[str, Any]: ...

    @abstractmethod
    def promote(self, plan: DeployPlan) -> dict[str, Any]: ...

    @abstractmethod
    def rollback(self, plan: DeployPlan) -> dict[str, Any]: ...

    @abstractmethod
    def metrics(self, plan: DeployPlan) -> dict[str, float]: ...


class SecretsAdapter(ABC):
    @abstractmethod
    def fetch(self, secrets_ref: str) -> dict[str, str]: ...


class CIAdapter(ABC):
    @abstractmethod
    def emit_billing_event(self, plan: DeployPlan, manifest: dict[str, Any]) -> str: ...


@dataclass
class InMemoryRegistry(RegistryAdapter):
    digests: dict[tuple[str, str], str] = field(default_factory=dict)
    signed: set[str] = field(default_factory=set)

    def register(self, name: str, version: str, digest: str, signed: bool = True) -> None:
        self.digests[(name, version)] = digest
        if signed:
            self.signed.add(digest)

    def resolve_digest(self, name: str, version: str) -> str:
        if (name, version) not in self.digests:
            raise KeyError(f"unknown model {name}:{version}")
        return self.digests[(name, version)]

    def is_signed(self, digest: str) -> bool:
        return digest in self.signed


@dataclass
class InMemoryRuntime(RuntimeAdapter):
    provisioned: set[str] = field(default_factory=set)
    canary_history: list[tuple[str, int]] = field(default_factory=list)
    promoted: set[str] = field(default_factory=set)
    rolled_back: set[str] = field(default_factory=set)
    fake_metrics: dict[str, float] = field(
        default_factory=lambda: {"p95_ms": 120.0, "error_rate": 0.002, "cost_usd_per_1k": 0.42}
    )

    def provision(self, plan: DeployPlan) -> dict[str, Any]:
        self.provisioned.add(plan.plan_id)
        return {"cluster": plan.target.cluster, "namespace": plan.target.namespace, "drift": 0}

    def deploy_canary(self, plan: DeployPlan, weight_pct: int) -> dict[str, Any]:
        self.canary_history.append((plan.plan_id, weight_pct))
        return {"weight": weight_pct, "image": plan.image_digest}

    def promote(self, plan: DeployPlan) -> dict[str, Any]:
        self.promoted.add(plan.plan_id)
        return {"alias": "prod", "weight": 100}

    def rollback(self, plan: DeployPlan) -> dict[str, Any]:
        self.rolled_back.add(plan.plan_id)
        return {"rolled_back": True}

    def metrics(self, plan: DeployPlan) -> dict[str, float]:
        return dict(self.fake_metrics)


@dataclass
class InMemorySecrets(SecretsAdapter):
    store: dict[str, dict[str, str]] = field(default_factory=dict)

    def fetch(self, secrets_ref: str) -> dict[str, str]:
        if secrets_ref not in self.store:
            raise KeyError(f"missing secret bundle {secrets_ref}")
        return dict(self.store[secrets_ref])


@dataclass
class InMemoryCI(CIAdapter):
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit_billing_event(self, plan: DeployPlan, manifest: dict[str, Any]) -> str:
        event_id = f"evt-{plan.plan_id}-{len(self.events) + 1}"
        self.events.append({"id": event_id, "plan_id": plan.plan_id, "manifest": manifest})
        return event_id
