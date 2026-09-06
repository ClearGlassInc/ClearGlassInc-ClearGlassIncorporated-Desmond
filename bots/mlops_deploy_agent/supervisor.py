# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Supervisor: idempotent state machine that drives a DeployPlan through stages."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .adapters import CIAdapter, RegistryAdapter, RuntimeAdapter, SecretsAdapter
from .policy import PolicyEngine
from .schema import AuditManifest, DeployPlan, StageResult
from .validator import StageValidators

SUPERVISOR_STAGES: tuple[str, ...] = (
    "intake",
    "resolve",
    "policy",
    "provision",
    "deploy",
    "verify",
    "promote",
    "audit",
    "monetize",
)


class StageFailure(Exception):
    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(f"stage {stage!r} failed: {reason}")
        self.stage = stage
        self.reason = reason


@dataclass
class Supervisor:
    registry: RegistryAdapter
    runtime: RuntimeAdapter
    secrets: SecretsAdapter
    ci: CIAdapter
    previous_chain_hash: str = "0" * 64
    checkpoints: list[StageResult] = field(default_factory=list)
    _validators: dict = field(default_factory=lambda: StageValidators.registry())

    def run(self, plan: DeployPlan) -> AuditManifest:
        self.checkpoints.clear()
        for stage in SUPERVISOR_STAGES:
            result = self._dispatch(stage, plan)
            if not self._validators[stage](plan, result):
                repaired = self._repair(stage, plan, result)
                if not self._validators[stage](plan, repaired):
                    if plan.rollback_on_fail:
                        self.runtime.rollback(plan)
                    raise StageFailure(stage, repaired.reason or "validation failed")
                result = repaired
            self.checkpoints.append(result)
        return self._build_manifest(plan)

    def _dispatch(self, stage: str, plan: DeployPlan) -> StageResult:
        handler = getattr(self, f"_stage_{stage}")
        try:
            return handler(plan)
        except Exception as exc:  # adapters surface real errors; convert to repairable status
            return StageResult(stage=stage, status="NEEDS_REPAIR", reason=str(exc))

    def _repair(self, stage: str, plan: DeployPlan, result: StageResult) -> StageResult:
        # Single deterministic retry. Real adapters may add idempotent compensation here.
        return self._dispatch(stage, plan)

    # --- stage handlers -------------------------------------------------

    def _stage_intake(self, plan: DeployPlan) -> StageResult:
        return StageResult(stage="intake", status="OK", data={"plan_id": plan.plan_id})

    def _stage_resolve(self, plan: DeployPlan) -> StageResult:
        resolved = self.registry.resolve_digest(plan.model.name, plan.model.version)
        if resolved != plan.model.digest:
            return StageResult(
                stage="resolve",
                status="NEEDS_REPAIR",
                reason=f"registry digest {resolved} != plan digest {plan.model.digest}",
            )
        return StageResult(
            stage="resolve",
            status="OK",
            data={"model_digest": resolved, "image_digest": plan.image_digest},
        )

    def _stage_policy(self, plan: DeployPlan) -> StageResult:
        violations = PolicyEngine(self.registry).evaluate(plan)
        status = "OK" if not violations else "NEEDS_REPAIR"
        return StageResult(
            stage="policy",
            status=status,
            data={"violations": violations},
            reason="; ".join(violations),
        )

    def _stage_provision(self, plan: DeployPlan) -> StageResult:
        # Fetching secrets validates the secrets_ref before provisioning runtime.
        self.secrets.fetch(plan.secrets_ref)
        info = self.runtime.provision(plan)
        return StageResult(stage="provision", status="OK", data=info)

    def _stage_deploy(self, plan: DeployPlan) -> StageResult:
        steps: list[int] = []
        for step in plan.target.canary_steps:
            self.runtime.deploy_canary(plan, step)
            steps.append(step)
        return StageResult(stage="deploy", status="OK", data={"steps_completed": steps})

    def _stage_verify(self, plan: DeployPlan) -> StageResult:
        metrics = self.runtime.metrics(plan)
        return StageResult(stage="verify", status="OK", data={"metrics": metrics})

    def _stage_promote(self, plan: DeployPlan) -> StageResult:
        info = self.runtime.promote(plan)
        return StageResult(stage="promote", status="OK", data=info)

    def _stage_audit(self, plan: DeployPlan) -> StageResult:
        chain_hash = self._chain_hash(plan)
        return StageResult(
            stage="audit",
            status="OK",
            data={"chain_hash": chain_hash, "signed": True},
        )

    def _stage_monetize(self, plan: DeployPlan) -> StageResult:
        event_id = self.ci.emit_billing_event(plan, {"plan_id": plan.plan_id})
        return StageResult(stage="monetize", status="OK", data={"event_id": event_id})

    # --- manifest -------------------------------------------------------

    def _chain_hash(self, plan: DeployPlan) -> str:
        payload: dict[str, Any] = {
            "previous": self.previous_chain_hash,
            "plan_id": plan.plan_id,
            "model_digest": plan.model.digest,
            "image_digest": plan.image_digest,
            "stages": [c.stage for c in self.checkpoints],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _build_manifest(self, plan: DeployPlan) -> AuditManifest:
        audit_checkpoint = next(c for c in self.checkpoints if c.stage == "audit")
        return AuditManifest(
            plan_id=plan.plan_id,
            image_digest=plan.image_digest,
            model_digest=plan.model.digest,
            stages=tuple(c.stage for c in self.checkpoints),
            chain_hash=audit_checkpoint.data["chain_hash"],
            signed=audit_checkpoint.data["signed"],
        )
