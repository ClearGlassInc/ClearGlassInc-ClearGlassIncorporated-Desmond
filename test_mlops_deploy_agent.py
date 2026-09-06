# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for the MLOps deploy agent supervisor, schema, and policy engine."""

from __future__ import annotations

import pytest

from bots.mlops_deploy_agent import (
    DeployPlan,
    InMemoryCI,
    InMemoryRegistry,
    InMemoryRuntime,
    InMemorySecrets,
    ModelRef,
    Policy,
    PolicyEngine,
    PolicyViolation,
    StageFailure,
    Supervisor,
    Target,
)

MODEL_DIGEST = "a" * 64
IMAGE_DIGEST = "b" * 64
OTHER_DIGEST = "c" * 64


def _make_plan(**overrides) -> DeployPlan:
    base = dict(
        plan_id="plan-001",
        model=ModelRef(registry="mlflow", name="ranker", version="2.4.0", digest=MODEL_DIGEST),
        target=Target(
            runtime="kserve",
            cluster="prod-east",
            namespace="ml",
            strategy="canary",
            canary_steps=(5, 50, 100),
        ),
        policy=Policy(max_p95_ms=200, cost_ceiling_usd_per_1k=1.0, max_error_rate=0.01),
        secrets_ref="ml/prod/api",
        image_digest=IMAGE_DIGEST,
    )
    base.update(overrides)
    return DeployPlan(**base)


def _bootstrap(plan: DeployPlan, sign_image: bool = True, sign_model: bool = True) -> Supervisor:
    registry = InMemoryRegistry()
    registry.register(plan.model.name, plan.model.version, plan.model.digest, signed=sign_model)
    if sign_image:
        registry.signed.add(plan.image_digest)
    secrets = InMemorySecrets(store={plan.secrets_ref: {"api_key": "x"}})
    return Supervisor(
        registry=registry,
        runtime=InMemoryRuntime(),
        secrets=secrets,
        ci=InMemoryCI(),
    )


# --- schema validation ----------------------------------------------------


def test_model_ref_rejects_non_sha256_digest() -> None:
    with pytest.raises(ValueError, match="digest"):
        ModelRef(registry="mlflow", name="x", version="1", digest="not-a-digest")


def test_target_rejects_descending_canary_steps() -> None:
    with pytest.raises(ValueError, match="ascending"):
        Target(
            runtime="kserve",
            cluster="c",
            namespace="n",
            strategy="canary",
            canary_steps=(100, 50, 5),
        )


def test_policy_rejects_invalid_error_rate() -> None:
    with pytest.raises(ValueError, match="max_error_rate"):
        Policy(max_p95_ms=100, cost_ceiling_usd_per_1k=1.0, max_error_rate=2.0)


def test_deploy_plan_requires_image_digest_sha256() -> None:
    with pytest.raises(ValueError, match="image_digest"):
        DeployPlan(
            plan_id="p",
            model=ModelRef(registry="mlflow", name="x", version="1", digest=MODEL_DIGEST),
            target=Target(runtime="kserve", cluster="c", namespace="n", strategy="canary"),
            policy=Policy(max_p95_ms=100, cost_ceiling_usd_per_1k=1.0),
            secrets_ref="r",
            image_digest="bad",
        )


# --- policy engine --------------------------------------------------------


def test_policy_passes_when_signed() -> None:
    plan = _make_plan()
    sup = _bootstrap(plan)
    assert PolicyEngine(sup.registry).evaluate(plan) == []


def test_policy_fails_when_image_unsigned() -> None:
    plan = _make_plan()
    sup = _bootstrap(plan, sign_image=False)
    violations = PolicyEngine(sup.registry).evaluate(plan)
    assert any("image" in v for v in violations)


def test_policy_enforce_raises() -> None:
    plan = _make_plan()
    sup = _bootstrap(plan, sign_image=False)
    with pytest.raises(PolicyViolation):
        PolicyEngine(sup.registry).enforce(plan)


# --- supervisor end-to-end -----------------------------------------------


def test_supervisor_completes_all_stages_and_emits_manifest() -> None:
    plan = _make_plan()
    sup = _bootstrap(plan)
    manifest = sup.run(plan)
    assert manifest.plan_id == plan.plan_id
    assert manifest.model_digest == MODEL_DIGEST
    assert manifest.image_digest == IMAGE_DIGEST
    assert manifest.signed is True
    assert len(manifest.chain_hash) == 64
    assert manifest.stages[0] == "intake"
    assert manifest.stages[-1] == "monetize"


def test_supervisor_canary_walk_matches_plan_steps() -> None:
    plan = _make_plan()
    sup = _bootstrap(plan)
    sup.run(plan)
    weights = [w for pid, w in sup.runtime.canary_history if pid == plan.plan_id]
    assert weights == list(plan.target.canary_steps)


def test_supervisor_rolls_back_when_digest_mismatches() -> None:
    plan = _make_plan()
    sup = _bootstrap(plan)
    # Inject a mismatching digest into the registry so resolve fails twice.
    sup.registry.digests[(plan.model.name, plan.model.version)] = OTHER_DIGEST
    with pytest.raises(StageFailure) as excinfo:
        sup.run(plan)
    assert excinfo.value.stage == "resolve"
    assert plan.plan_id in sup.runtime.rolled_back


def test_supervisor_fails_policy_stage_when_unsigned() -> None:
    plan = _make_plan()
    sup = _bootstrap(plan, sign_image=False)
    with pytest.raises(StageFailure) as excinfo:
        sup.run(plan)
    assert excinfo.value.stage == "policy"


def test_supervisor_fails_verify_when_metrics_breach_slo() -> None:
    plan = _make_plan(policy=Policy(max_p95_ms=10, cost_ceiling_usd_per_1k=1.0))
    sup = _bootstrap(plan)
    with pytest.raises(StageFailure) as excinfo:
        sup.run(plan)
    assert excinfo.value.stage == "verify"
    assert plan.plan_id in sup.runtime.rolled_back


def test_supervisor_emits_billing_event() -> None:
    plan = _make_plan()
    sup = _bootstrap(plan)
    sup.run(plan)
    assert len(sup.ci.events) == 1
    assert sup.ci.events[0]["plan_id"] == plan.plan_id


def test_chain_hash_is_deterministic_for_same_inputs() -> None:
    plan = _make_plan()
    sup_a = _bootstrap(plan)
    sup_b = _bootstrap(plan)
    assert sup_a.run(plan).chain_hash == sup_b.run(plan).chain_hash
