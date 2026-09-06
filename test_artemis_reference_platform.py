import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

MODULE_PATH = Path("platform/artemis_reference/self_evolving_platform.py")
SPEC = importlib.util.spec_from_file_location("artemis_reference", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
artemis_reference = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = artemis_reference
SPEC.loader.exec_module(artemis_reference)

Classification = artemis_reference.Classification
Decision = artemis_reference.Decision
EvalMetrics = artemis_reference.EvalMetrics
MissionContext = artemis_reference.MissionContext
Principal = artemis_reference.Principal
UpgradeProposal = artemis_reference.UpgradeProposal
evaluate_need_to_know = artemis_reference.evaluate_need_to_know
hash_payload = artemis_reference.hash_payload
make_signal = artemis_reference.make_signal
submit_upgrade_proposal = artemis_reference.submit_upgrade_proposal


def test_payload_hash_is_stable_across_nested_key_order() -> None:
    first = {"signal": {"bearing": 42, "labels": ["alpha", "bravo"]}, "active": True}
    second = {"active": True, "signal": {"labels": ["alpha", "bravo"], "bearing": 42}}

    assert hash_payload(first) == hash_payload(second)


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan"), float("inf")])
def test_make_signal_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence must be a finite value"):
        make_signal({"confidence": confidence}, "mission-1", "sensor-1")


@pytest.mark.parametrize(("mission_id", "source_system"), [("", "sensor-1"), ("mission-1", " ")])
def test_make_signal_rejects_missing_scope(mission_id: str, source_system: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        make_signal({}, mission_id, source_system)


def test_hash_payload_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match="Out of range float values"):
        hash_payload({"reading": float("nan")})


def test_operational_action_requires_human_approval() -> None:
    principal = Principal(
        subject="operator-1",
        role="analyst",
        clearance=Classification.SECRET,
        coalitions=frozenset({"US"}),
        compartments=frozenset({"ARTEMIS-ALPHA"}),
        mission_scope=frozenset({"mission-1"}),
    )
    mission = MissionContext(
        mission_id="mission-1",
        classification=Classification.SECRET,
        required_compartments=frozenset({"ARTEMIS-ALPHA"}),
        coalitions=frozenset({"US"}),
        latency_budget_ms=2_500,
    )

    decision = evaluate_need_to_know(principal, mission, "execute_response", True)

    assert decision.decision is Decision.APPROVAL


def test_upgrade_requires_passing_evals_and_human_review() -> None:
    proposal = UpgradeProposal(
        proposal_id="upgrade-1",
        target="prompt",
        current_version="v1",
        candidate_version="v2",
        evidence_metrics=EvalMetrics(0.95, 0.90, 0.01, 800.0, 0, 0.85),
        risk_notes=("canary only",),
    )

    reviewed = submit_upgrade_proposal(proposal, reviewer=lambda candidate: candidate.target == "prompt")

    assert reviewed.status == "approved_for_apollo_canary"


def test_failing_upgrade_does_not_reach_human_review() -> None:
    proposal = UpgradeProposal(
        proposal_id="upgrade-unsafe",
        target="model_router",
        current_version="v1",
        candidate_version="v2",
        evidence_metrics=EvalMetrics(0.95, 0.90, 0.01, 800.0, 1, 0.85),
        risk_notes=("policy violation observed",),
    )
    reviewer_called = False

    def reviewer(_proposal: object) -> bool:
        nonlocal reviewer_called
        reviewer_called = True
        return True

    reviewed = submit_upgrade_proposal(proposal, reviewer=reviewer)

    assert reviewed.status == "rejected_by_eval_gate"
    assert reviewer_called is False


def test_payload_hash_matches_canonical_json_sha256() -> None:
    payload = {"message": "Artemis", "priority": 1}
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    assert len(hash_payload(payload)) == 64
    assert hash_payload(payload) == hashlib.sha256(canonical.encode()).hexdigest()
