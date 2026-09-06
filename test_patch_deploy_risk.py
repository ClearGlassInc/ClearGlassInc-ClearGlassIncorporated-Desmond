"""Unit tests for the Enterprise Patch & Deploy risk/confidence engine.

Covers the production-readiness checklist item "Confidence threshold logic
unit-tested" plus the doc §3 control model and §4 stop-loss guardrails.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.patch_deploy.risk_score import (
    AUTONOMOUS_CONFIDENCE,
    Change,
    RepoInventory,
    change_id,
    classify,
    confidence_gate,
    risk_score,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _low_risk_inv() -> RepoInventory:
    return RepoInventory(
        repo="static-site",
        criticality=1.0,
        internet_facing=False,
        handles_customer_data=False,
        fleet_fraction=0.05,
    )


def _high_risk_inv() -> RepoInventory:
    return RepoInventory(
        repo="clearglass-commerce",
        criticality=5.0,
        internet_facing=True,
        handles_customer_data=True,
        fleet_fraction=0.5,
    )


# --- idempotency -----------------------------------------------------------


def test_change_id_is_deterministic():
    c1 = Change("Repo", "dependency_bump", content_ref="abc123", target_env="Staging")
    c2 = Change("repo", "dependency-bump", content_ref="abc123", target_env="staging")
    # Case/format normalization means these are the *same* logical change.
    assert change_id(c1) == change_id(c2)


def test_change_id_changes_with_content():
    base = Change("repo", "dependency_bump", content_ref="abc123")
    other = Change("repo", "dependency_bump", content_ref="def456")
    assert change_id(base) != change_id(other)


# --- risk scoring ----------------------------------------------------------


def test_low_risk_dependency_bump_scores_low():
    change = Change("static-site", "dependency_bump", cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    assert card.risk_class == "low"
    assert card.score < 25.0


def test_critical_cvss_floors_to_high_or_above_even_in_small_repo():
    change = Change("static-site", "security_hotfix", cvss=9.8)
    card = risk_score(change, _low_risk_inv())
    assert card.risk_class in ("high", "critical")
    assert card.score >= 75.0


def test_missing_inventory_escalates_to_worst_case():
    change = Change("unknown-repo", "app_release", cvss=5.0)
    card = risk_score(change, None)
    # Worst-case factors assumed -> not classified low.
    assert card.risk_class != "low"
    assert "escalated" in card.rationale


# --- confidence gate: the three bands --------------------------------------


def test_autonomous_requires_low_risk_and_high_confidence():
    change = Change("static-site", "dependency_bump", cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    _, decision = card, confidence_gate(card, 0.95)
    assert decision.verdict == "autonomous"


def test_just_below_autonomous_threshold_needs_approval():
    change = Change("static-site", "dependency_bump", cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    decision = confidence_gate(card, AUTONOMOUS_CONFIDENCE - 0.01)
    assert decision.verdict == "approval"


def test_exactly_at_threshold_is_autonomous():
    change = Change("static-site", "dependency_bump", cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    decision = confidence_gate(card, AUTONOMOUS_CONFIDENCE)
    assert decision.verdict == "autonomous"


def test_below_floor_is_hard_stop():
    change = Change("static-site", "dependency_bump", cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    decision = confidence_gate(card, 0.74)
    assert decision.verdict == "hard_stop"


# --- unconditional stop-loss -----------------------------------------------


def test_critical_gate_failure_forces_hard_stop_even_at_full_confidence():
    change = Change("static-site", "dependency_bump", cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    decision = confidence_gate(card, 1.0, critical_gate_failure=True)
    assert decision.verdict == "hard_stop"


def test_contradictory_results_forces_hard_stop():
    change = Change("static-site", "dependency_bump", cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    decision = confidence_gate(card, 1.0, contradictory_results=True)
    assert decision.verdict == "hard_stop"


# --- never-autonomous / always-approval change types -----------------------


@pytest.mark.parametrize(
    "change_type",
    ["secret_rotation", "privileged", "inventory_change", "risk_model_change"],
)
def test_never_autonomous_types_cannot_auto_execute(change_type):
    change = Change("static-site", change_type, cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    decision = confidence_gate(card, 1.0)  # even at perfect confidence
    assert decision.verdict == "approval"


@pytest.mark.parametrize(
    "change_type",
    ["config_change", "policy_change", "production_traffic_shift"],
)
def test_always_approval_types_never_autonomous(change_type):
    change = Change("static-site", change_type, cvss=0.0)
    card = risk_score(change, _low_risk_inv())
    decision = confidence_gate(card, 1.0)
    assert decision.verdict == "approval"


def test_high_risk_change_needs_approval_even_with_high_confidence():
    change = Change("clearglass-commerce", "app_release", cvss=8.0)
    card = risk_score(change, _high_risk_inv())
    assert card.risk_class in ("high", "critical")
    decision = confidence_gate(card, 0.99)
    assert decision.verdict == "approval"


# --- CLI contract (exit codes consumed by the workflow) --------------------


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scripts.patch_deploy.risk_score", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_cli_autonomous_exit_zero():
    proc = _run_cli(
        "--repo", "static-site",
        "--change-type", "dependency_bump",
        "--content-ref", "deadbeef",
        "--confidence", "0.99",
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["decision"]["verdict"] == "autonomous"


def test_cli_hard_stop_exit_two():
    proc = _run_cli(
        "--repo", "static-site",
        "--change-type", "dependency_bump",
        "--content-ref", "deadbeef",
        "--confidence", "0.10",
    )
    assert proc.returncode == 2, proc.stderr


def test_classify_returns_matching_change_id():
    change = Change("static-site", "dependency_bump", content_ref="xyz")
    card, decision = classify(change, _low_risk_inv(), 0.99)
    assert card.change_id == decision.change_id == change_id(change)
