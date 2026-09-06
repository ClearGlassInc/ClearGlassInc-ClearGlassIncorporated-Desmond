# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Per-stage validators. Each returns True iff the stage result satisfies its rule."""

from __future__ import annotations

from typing import Callable

from .schema import DeployPlan, StageResult

ValidatorFn = Callable[[DeployPlan, StageResult], bool]


class StageValidators:
    @staticmethod
    def intake(plan: DeployPlan, result: StageResult) -> bool:
        return result.ok and result.data.get("plan_id") == plan.plan_id

    @staticmethod
    def resolve(plan: DeployPlan, result: StageResult) -> bool:
        return (
            result.ok
            and result.data.get("model_digest") == plan.model.digest
            and result.data.get("image_digest") == plan.image_digest
        )

    @staticmethod
    def policy(plan: DeployPlan, result: StageResult) -> bool:
        return result.ok and result.data.get("violations") == []

    @staticmethod
    def provision(plan: DeployPlan, result: StageResult) -> bool:
        return result.ok and result.data.get("drift", 1) == 0

    @staticmethod
    def deploy(plan: DeployPlan, result: StageResult) -> bool:
        steps = result.data.get("steps_completed", [])
        return result.ok and steps == list(plan.target.canary_steps)

    @staticmethod
    def verify(plan: DeployPlan, result: StageResult) -> bool:
        if not result.ok:
            return False
        metrics = result.data.get("metrics", {})
        return (
            metrics.get("p95_ms", float("inf")) <= plan.policy.max_p95_ms
            and metrics.get("error_rate", 1.0) <= plan.policy.max_error_rate
            and metrics.get("cost_usd_per_1k", float("inf")) <= plan.policy.cost_ceiling_usd_per_1k
        )

    @staticmethod
    def promote(plan: DeployPlan, result: StageResult) -> bool:
        return result.ok and result.data.get("alias") == "prod" and result.data.get("weight") == 100

    @staticmethod
    def audit(plan: DeployPlan, result: StageResult) -> bool:
        return result.ok and bool(result.data.get("chain_hash")) and result.data.get("signed") is True

    @staticmethod
    def monetize(plan: DeployPlan, result: StageResult) -> bool:
        return result.ok and bool(result.data.get("event_id"))

    @classmethod
    def registry(cls) -> dict[str, ValidatorFn]:
        return {
            "intake": cls.intake,
            "resolve": cls.resolve,
            "policy": cls.policy,
            "provision": cls.provision,
            "deploy": cls.deploy,
            "verify": cls.verify,
            "promote": cls.promote,
            "audit": cls.audit,
            "monetize": cls.monetize,
        }
