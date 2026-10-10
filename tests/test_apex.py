"""Regression tests for APEX planning, governance and quantum-claim boundaries."""
from __future__ import annotations

import pytest

from app.apex_core import (
    APEXInputError,
    BenchmarkSummary,
    EvidenceRef,
    compare_benchmarks,
    create_plan,
)
from app.governance import score_action


def test_plan_is_explicitly_non_executing_and_integrates_governance() -> None:
    plan = create_plan(
        mission_id="MISSION-1",
        objective="Review current security architecture and identify evidence gaps.",
        requested_action="deploy_high_risk_change",
        sources=(EvidenceRef("ARCH-1", "repo://docs/security.md", "a" * 64),),
        fingerprint_key="test-key",
    ).to_dict()

    assert plan["status"] == "planned_only"
    assert plan["execution_status"] == "not_executed"
    assert plan["external_side_effects"] is False
    assert plan["action_assessment"]["requires_approval"] is True
    assert plan["plan_assessment"]["action"] == "apex_plan_mission"
    assert [step["specialist"] for step in plan["steps"]][:4] == [
        "CORTEX", "ARTEMIS", "AEGIS", "SENTINEL"
    ]
    assert plan["sources"][0]["digest_status"] == "declared_not_verified"


def test_duplicate_source_ids_are_rejected() -> None:
    source = EvidenceRef("DUP-1", "repo://docs/one.md")
    with pytest.raises(APEXInputError, match="unique"):
        create_plan(
            mission_id="MISSION-DUP",
            objective="Review this system and make a recommendation.",
            sources=(source, source),
        )


def test_unknown_actions_stay_fail_closed_through_apex() -> None:
    plan = create_plan(
        mission_id="MISSION-2",
        objective="Review this system and make a recommendation.",
        requested_action="future_unregistered_action",
        sources=(EvidenceRef("SRC-1", "https://example.org/report"),),
    )
    assert plan.action_assessment.requires_approval
    assert plan.action_assessment.score >= 60


def test_missing_evidence_escalates_even_low_risk_actions() -> None:
    plan = create_plan(
        mission_id="MISSION-3",
        objective="Review this system and make a recommendation.",
        requested_action="apex_plan_mission",
    )
    assert plan.action_assessment.requires_approval
    assert any("low confidence" in reason for reason in plan.action_assessment.reasons)


def test_invalid_source_digest_and_uri_are_rejected() -> None:
    with pytest.raises(APEXInputError):
        EvidenceRef("SRC-1", "https://user:password@example.org/private")
    with pytest.raises(APEXInputError):
        EvidenceRef("SRC-2", "javascript:alert(1)")
    with pytest.raises(APEXInputError):
        EvidenceRef("SRC-4", "https://[malformed")
    with pytest.raises(APEXInputError):
        EvidenceRef("SRC-3", "repo://docs/file.md", "not-a-digest")


def test_quantum_research_is_a_protocol_not_a_live_backend() -> None:
    plan = create_plan(
        mission_id="MISSION-Q",
        objective="Evaluate quantum optimization against a classical scheduling baseline.",
        sources=(EvidenceRef("BENCH-1", "repo://benchmarks/schedule.json"),),
    ).to_dict()
    assert plan["quantum_research"]["included"] is True
    assert plan["quantum_research"]["status"] == "benchmark_design_only"
    assert plan["quantum_research"]["quantum_job_submitted"] is False
    assert plan["quantum_research"]["quantum_advantage_claimed"] is False


def test_quantum_comparison_rejects_different_problem_or_constraints() -> None:
    candidate = BenchmarkSummary("problem-a", "constraints-a", "quantum_simulator", 10, 4, 50)
    baseline = BenchmarkSummary("problem-b", "constraints-a", "classical", 20, 5, 50)
    result = compare_benchmarks(candidate, baseline)
    assert result["status"] == "not_comparable"
    assert result["quantum_advantage_claimed"] is False


def test_quantum_improvement_is_never_auto_promoted_to_advantage() -> None:
    candidate = BenchmarkSummary("problem-a", "constraints-a", "quantum_hardware", 10, 4, 40)
    baseline = BenchmarkSummary("problem-a", "constraints-a", "classical", 20, 5, 40)
    result = compare_benchmarks(candidate, baseline)
    assert result["status"] == "candidate_improvement_requires_independent_review"
    assert result["quantum_advantage_claimed"] is False
    assert "No quantum advantage demonstrated" in result["permitted_claim"]


def test_governance_kernel_still_provides_risk_explanation() -> None:
    assessment = score_action("apex_plan_mission")
    assert assessment.score == 5
    assert not assessment.requires_approval
    assert assessment.reasons


def test_control_plane_wires_apex_through_the_existing_admin_surface() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    main = (root / "control-plane" / "app" / "main.py").read_text(encoding="utf-8")
    router = (root / "control-plane" / "app" / "routers" / "apex.py").read_text(encoding="utf-8")

    assert "    apex," in main
    assert "app.include_router(apex.router, dependencies=admin)" in main
    assert "actor: str = Depends(require_admin)" in router
    assert "log_event(" in router
    assert 'action="apex_plan_mission"' in router


def test_apex_route_declines_sensitive_inputs_before_creating_a_plan() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    router = (root / "control-plane" / "app" / "routers" / "apex.py").read_text(encoding="utf-8")
    guard = router.index("if _SENSITIVE_INPUT.search(supplied_text):")
    planner = router.index("plan = apex_core.create_plan(")
    assert guard < planner
    assert "no plan was created" in router
