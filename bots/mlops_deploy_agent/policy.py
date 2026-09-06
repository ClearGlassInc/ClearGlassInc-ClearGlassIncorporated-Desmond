# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Policy engine: deterministic OPA-style gates evaluated before deploy."""

from __future__ import annotations

from dataclasses import dataclass

from .adapters import RegistryAdapter
from .schema import DeployPlan


class PolicyViolation(Exception):
    """Raised when a hard policy gate fails."""


@dataclass
class PolicyEngine:
    registry: RegistryAdapter

    def evaluate(self, plan: DeployPlan) -> list[str]:
        violations: list[str] = []
        if plan.policy.require_signed and not self.registry.is_signed(plan.model.digest):
            violations.append("model artifact is not signed")
        if plan.policy.require_signed and not self.registry.is_signed(plan.image_digest):
            violations.append("container image is not signed")
        if plan.policy.max_p95_ms <= 0:
            violations.append("policy.max_p95_ms must be positive")
        if plan.policy.cost_ceiling_usd_per_1k <= 0:
            violations.append("policy.cost_ceiling_usd_per_1k must be positive")
        return violations

    def enforce(self, plan: DeployPlan) -> None:
        violations = self.evaluate(plan)
        if violations:
            raise PolicyViolation("; ".join(violations))
