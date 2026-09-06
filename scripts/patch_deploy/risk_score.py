#!/usr/bin/env python3
"""Risk classification + confidence gating for Enterprise Patch & Deploy.

Implements the triage math and control model from
``docs/ENTERPRISE_PATCH_DEPLOY.md``:

    risk_score = CVSS x exposure x data_sensitivity x blast_radius   (0..100)

and the confidence gate:

    autonomous  : confidence >= 0.92 and risk_class in {low}          (+ no critical gate fail)
    approval     : 0.75 <= confidence < 0.92, or risk_class in {medium, high, critical}
    hard_stop    : confidence < 0.75, or any critical gate failure

Some change types are *never* auto-executed regardless of score (secret
rotation / privileged, inventory or risk-model changes) — see NEVER_AUTONOMOUS.

Stdlib-only so it runs in a minimal CI runner. Exit codes from ``main`` are
consumable by ``.github/workflows/enterprise-patch-deploy.yml``:

    0 = autonomous   1 = approval-required   2 = hard-stop   3 = usage/input error
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import hashlib
import json
import sys
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Control-model constants (single source of truth; unit-tested).
# ---------------------------------------------------------------------------

AUTONOMOUS_CONFIDENCE = 0.92
APPROVAL_FLOOR = 0.75

# Categorical risk bands keyed off the normalized 0..100 score.
RISK_BANDS = (
    ("low", 0.0, 25.0),
    ("medium", 25.0, 50.0),
    ("high", 50.0, 75.0),
    ("critical", 75.0, 100.01),
)

# Change types that are NEVER auto-executed (doc §3 "Never Auto-Executed").
NEVER_AUTONOMOUS = frozenset(
    {
        "secret_rotation",
        "privileged",
        "inventory_change",
        "risk_model_change",
    }
)

# Change types that always require human approval even at low score (doc §3).
ALWAYS_APPROVAL = frozenset(
    {
        "config_change",
        "policy_change",
        "production_traffic_shift",
    }
    | set(NEVER_AUTONOMOUS)
)

VALID_VERDICTS = ("autonomous", "approval", "hard_stop")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RepoInventory:
    """One row of the repo criticality matrix (blast-radius inputs)."""

    repo: str
    criticality: float = 1.0  # 1..5 business criticality multiplier baseline
    internet_facing: bool = False
    handles_customer_data: bool = False
    fleet_fraction: float = 0.0  # share of the fleet this repo represents, 0..1

    @classmethod
    def from_dict(cls, repo: str, d: dict[str, Any]) -> "RepoInventory":
        return cls(
            repo=repo,
            criticality=float(d.get("criticality", 1.0)),
            internet_facing=bool(d.get("internet_facing", False)),
            handles_customer_data=bool(d.get("handles_customer_data", False)),
            fleet_fraction=float(d.get("fleet_fraction", 0.0)),
        )


@dataclass(frozen=True)
class Change:
    """A proposed change entering intake."""

    repo: str
    change_type: str
    summary: str = ""
    content_ref: str = ""  # diff hash, lockfile digest, commit sha, etc.
    cvss: float = 0.0  # 0..10 (0 for non-security changes)
    target_env: str = "staging"

    def normalized_type(self) -> str:
        return self.change_type.strip().lower().replace("-", "_").replace(" ", "_")


@dataclass(frozen=True)
class RiskCard:
    """Immutable triage output — the audit "risk score card"."""

    change_id: str
    repo: str
    change_type: str
    cvss: float
    exposure: float
    data_sensitivity: float
    blast_radius: float
    score: float
    risk_class: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class Decision:
    """Final gate decision for a change."""

    change_id: str
    verdict: str  # one of VALID_VERDICTS
    risk_class: str
    confidence: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def change_id(change: Change) -> str:
    """Deterministic id = hash(content + target). Enables idempotent re-runs.

    Re-running the same logical change yields the same id, so the state
    machine can treat a repeat as a no-op (doc §3 "Idempotency").
    """

    basis = "|".join(
        [
            change.repo.strip().lower(),
            change.normalized_type(),
            change.content_ref.strip(),
            change.target_env.strip().lower(),
        ]
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _band(score: float) -> str:
    for name, lo, hi in RISK_BANDS:
        if lo <= score < hi:
            return name
    return "critical"


def risk_score(change: Change, inv: RepoInventory | None) -> RiskCard:
    """Compute ``CVSS x exposure x data_sensitivity x blast_radius`` -> 0..100.

    Each factor is normalized to 0..1, the product is scaled to 0..100, and a
    security-change floor keeps a high-CVSS hotfix from being scored *low* just
    because it lands in a small repo.
    """

    if inv is None:
        # Missing inventory -> escalate (doc §2 Triage "Failure"). We do not
        # silently assume low blast radius; we assume the worst plausible.
        inv = RepoInventory(
            repo=change.repo,
            criticality=5.0,
            internet_facing=True,
            handles_customer_data=True,
            fleet_fraction=1.0,
        )
        inventory_note = "no inventory row (escalated: worst-case factors assumed)"
    else:
        inventory_note = f"inventory criticality={inv.criticality}"

    # Factor 1: CVSS severity, 0..10 -> 0..1 (non-security change => small base).
    cvss = _clamp(change.cvss, 0.0, 10.0)
    cvss_f = cvss / 10.0 if cvss > 0 else 0.2

    # Factor 2: exposure — internet-facing surfaces amplify risk.
    exposure_f = 1.0 if inv.internet_facing else 0.5

    # Factor 3: data sensitivity — customer data amplifies risk.
    data_f = 1.0 if inv.handles_customer_data else 0.4

    # Factor 4: blast radius — criticality (1..5) blended with fleet fraction.
    crit_f = _clamp(inv.criticality, 1.0, 5.0) / 5.0
    fleet_f = _clamp(inv.fleet_fraction, 0.0, 1.0)
    blast_f = _clamp(0.6 * crit_f + 0.4 * max(fleet_f, 0.25), 0.0, 1.0)

    score = 100.0 * cvss_f * exposure_f * data_f * blast_f

    # Security floor: a CVSS >= 9.0 change is at least "high" regardless of the
    # multiplicative dampening from a small/low-sensitivity repo.
    if cvss >= 9.0:
        score = max(score, 75.0)
    elif cvss >= 7.0:
        score = max(score, 50.0)

    score = round(_clamp(score, 0.0, 100.0), 2)
    risk_class = _band(score)

    rationale = (
        f"cvss={cvss:.1f}(f={cvss_f:.2f}) exposure={exposure_f:.2f} "
        f"data_sensitivity={data_f:.2f} blast_radius={blast_f:.2f}; "
        f"{inventory_note}"
    )

    return RiskCard(
        change_id=change_id(change),
        repo=change.repo,
        change_type=change.normalized_type(),
        cvss=cvss,
        exposure=exposure_f,
        data_sensitivity=data_f,
        blast_radius=blast_f,
        score=score,
        risk_class=risk_class,
        rationale=rationale,
    )


def confidence_gate(
    card: RiskCard,
    confidence: float,
    *,
    critical_gate_failure: bool = False,
    contradictory_results: bool = False,
) -> Decision:
    """Map (risk class, confidence, gate signals) -> autonomous/approval/hard_stop.

    Encodes the control model + safety guardrails: a critical gate failure or
    contradictory test results are an unconditional hard stop (doc §4, §6).
    """

    reasons: list[str] = []
    confidence = _clamp(float(confidence), 0.0, 1.0)

    # --- Unconditional hard stops (stop-loss) ---
    if critical_gate_failure:
        reasons.append("critical gate failure")
        return Decision(card.change_id, "hard_stop", card.risk_class, confidence, reasons)
    if contradictory_results:
        reasons.append("contradictory test results — human review required")
        return Decision(card.change_id, "hard_stop", card.risk_class, confidence, reasons)
    if confidence < APPROVAL_FLOOR:
        reasons.append(f"confidence {confidence:.2f} < hard-stop floor {APPROVAL_FLOOR}")
        return Decision(card.change_id, "hard_stop", card.risk_class, confidence, reasons)

    # --- Change types that are never autonomous / always need approval ---
    if card.change_type in NEVER_AUTONOMOUS:
        reasons.append(f"change_type '{card.change_type}' is never auto-executed")
        return Decision(card.change_id, "approval", card.risk_class, confidence, reasons)
    if card.change_type in ALWAYS_APPROVAL:
        reasons.append(f"change_type '{card.change_type}' always requires approval")
        return Decision(card.change_id, "approval", card.risk_class, confidence, reasons)

    # --- Autonomous path: low risk + high confidence only ---
    if card.risk_class == "low" and confidence >= AUTONOMOUS_CONFIDENCE:
        reasons.append(
            f"low risk and confidence {confidence:.2f} >= {AUTONOMOUS_CONFIDENCE}"
        )
        return Decision(card.change_id, "autonomous", card.risk_class, confidence, reasons)

    # --- Everything else in [0.75, 1.0]: proceed with approval ---
    if card.risk_class != "low":
        reasons.append(f"risk_class '{card.risk_class}' requires approval")
    else:
        reasons.append(
            f"confidence {confidence:.2f} in approval band "
            f"[{APPROVAL_FLOOR}, {AUTONOMOUS_CONFIDENCE})"
        )
    return Decision(card.change_id, "approval", card.risk_class, confidence, reasons)


def classify(
    change: Change,
    inv: RepoInventory | None,
    confidence: float,
    *,
    critical_gate_failure: bool = False,
    contradictory_results: bool = False,
) -> tuple[RiskCard, Decision]:
    """Convenience: triage + gate in one call."""

    card = risk_score(change, inv)
    decision = confidence_gate(
        card,
        confidence,
        critical_gate_failure=critical_gate_failure,
        contradictory_results=contradictory_results,
    )
    return card, decision


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


_VERDICT_EXIT = {"autonomous": 0, "approval": 1, "hard_stop": 2}


def _load_inventory(path: str | None, repo: str) -> RepoInventory | None:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    repos = data.get("repos", data)
    row = repos.get(repo)
    if row is None:
        return None
    return RepoInventory.from_dict(repo, row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Triage a change and emit a gate decision (risk card + verdict)."
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--change-type", required=True)
    parser.add_argument("--summary", default="")
    parser.add_argument("--content-ref", default="", help="diff/lockfile/commit digest")
    parser.add_argument("--cvss", type=float, default=0.0)
    parser.add_argument("--target-env", default="staging")
    parser.add_argument("--confidence", type=float, default=1.0)
    parser.add_argument("--inventory", default=None, help="path to repo-inventory JSON")
    parser.add_argument("--critical-gate-failure", action="store_true")
    parser.add_argument("--contradictory-results", action="store_true")
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="also emit key=value lines to $GITHUB_OUTPUT",
    )
    args = parser.parse_args(argv)

    change = Change(
        repo=args.repo,
        change_type=args.change_type,
        summary=args.summary,
        content_ref=args.content_ref,
        cvss=args.cvss,
        target_env=args.target_env,
    )
    inv = _load_inventory(args.inventory, args.repo)
    card, decision = classify(
        change,
        inv,
        args.confidence,
        critical_gate_failure=args.critical_gate_failure,
        contradictory_results=args.contradictory_results,
    )

    record = {
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "risk_card": card.to_dict(),
        "decision": decision.to_dict(),
    }
    print(json.dumps(record, indent=2))

    if args.github_output:
        _emit_github_output(card, decision)

    return _VERDICT_EXIT.get(decision.verdict, 3)


def _emit_github_output(card: RiskCard, decision: Decision) -> None:
    import os

    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"change_id={card.change_id}\n")
        fh.write(f"risk_class={card.risk_class}\n")
        fh.write(f"score={card.score}\n")
        fh.write(f"verdict={decision.verdict}\n")
        fh.write(f"confidence={decision.confidence}\n")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
