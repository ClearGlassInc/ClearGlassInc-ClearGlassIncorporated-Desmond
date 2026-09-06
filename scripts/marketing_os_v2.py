# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#!/usr/bin/env python3
"""Marketing Operating System v2.0 governance engine.

Stdlib-only enforcement layer for the enterprise multi-agent governance
prompt in ``agents/clearglass_marketing_os_v2/system_prompt.md``:

- validates initiative packets (mandatory fields, in-range scores, known
  Owner Bot) and, when anything is missing, returns *only* the list of
  missing fields — the minimum additional information required;
- computes the weighted Priority Score and ranks initiatives;
- runs the fail-closed quality gates (completeness, evidence, brand &
  claims, governance tier) and routes each initiative by risk tier;
- loads/validates the version-controlled shared memory and appends to it
  (append-only — existing entries are never removed or overwritten).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHARED_MEMORY_PATH = ROOT / "data" / "marketing-os" / "shared_memory.json"

PRIORITY_WEIGHTS: dict[str, float] = {
    "revenue_impact": 0.35,
    "lead_quality": 0.25,
    "strategic_fit": 0.20,
    "speed_to_execute": 0.10,
    "confidence": 0.10,
}

MANDATORY_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "owner_bot",
    "reasoning",
    "evidence",
    "expected_outcome",
    "success_metric",
    "target",
    "next_action",
    "confidence",
    "scores",
    "risk_tier",
)

VALID_OWNER_BOTS: frozenset[str] = frozenset(
    {
        "ORCH-00", "INTEL-01", "SEO-02", "PLAN-03", "WRITE-04",
        "SOCIAL-05", "VIDEO-06", "EMAIL-07", "LEADGEN-08", "CRO-09",
        "ANALYTICS-10", "COMPETE-11", "COMMUNITY-12", "PARTNER-13", "GOV-14",
    }
)

RISK_DISPOSITIONS: dict[str, str] = {
    "low": "auto_execute_and_log",
    "medium": "queue_approval",
    "high": "blocked_pending_approval",
    "critical": "blocked_pending_approval",
}

BANNED_PHRASES: tuple[str, ...] = (
    "revolutionary solution",
    "cutting-edge",
    "game changer",
    "guaranteed results",
    "#1 in the industry",
)

MIN_ADVANCE_CONFIDENCE = 40

MEMORY_SCHEMA: dict[str, tuple[str, ...]] = {
    "audience": ("personas", "pain_points", "objections", "buying_triggers"),
    "positioning": ("value_propositions", "differentiators", "proof_points"),
    "campaigns": ("active", "historical", "performance"),
    "content": ("inventory", "top_performers", "failed_assets"),
    "seo": ("keywords", "rankings", "topic_clusters"),
    "sales": ("opportunities", "objections", "win_loss_data"),
    "experiments": ("active_tests", "completed_tests", "lessons_learned"),
    "compliance": ("claims_library", "approved_language"),
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class GateResult:
    name: str
    passed: bool
    reason: str


@dataclass
class Evaluation:
    packet_id: str
    priority_score: float
    gates: list[GateResult] = field(default_factory=list)
    disposition: str = "blocked_pending_approval"

    @property
    def advanced(self) -> bool:
        return all(gate.passed for gate in self.gates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "priority_score": self.priority_score,
            "advanced": self.advanced,
            "disposition": self.disposition,
            "gates": [
                {"name": g.name, "passed": g.passed, "reason": g.reason}
                for g in self.gates
            ],
        }


def missing_fields(packet: dict[str, Any]) -> list[str]:
    """Return the minimum additional information required, and nothing else."""
    missing = [name for name in MANDATORY_FIELDS if not packet.get(name)]
    scores = packet.get("scores")
    if isinstance(scores, dict):
        for key in PRIORITY_WEIGHTS:
            value = scores.get(key)
            if not isinstance(value, (int, float)) or not 0 <= value <= 100:
                missing.append(f"scores.{key}")
    confidence = packet.get("confidence")
    if confidence is not None and (
        not isinstance(confidence, (int, float)) or not 0 <= confidence <= 100
    ):
        missing.append("confidence (must be 0-100)")
    owner = packet.get("owner_bot")
    if owner and owner not in VALID_OWNER_BOTS:
        missing.append(f"owner_bot (unknown bot '{owner}')")
    tier = packet.get("risk_tier")
    if tier and tier not in RISK_DISPOSITIONS:
        missing.append(f"risk_tier (must be one of {sorted(RISK_DISPOSITIONS)})")
    return missing


def priority_score(scores: dict[str, Any]) -> float:
    """Weighted Priority Score, 0-100."""
    return round(
        sum(float(scores[key]) * weight for key, weight in PRIORITY_WEIGHTS.items()),
        2,
    )


def _packet_text(packet: dict[str, Any]) -> str:
    parts = [
        str(packet.get(key, ""))
        for key in ("title", "reasoning", "expected_outcome", "next_action")
    ]
    return " ".join(parts).lower()


def run_gates(packet: dict[str, Any], memory: dict[str, Any]) -> list[GateResult]:
    """Run the four quality gates in order. A gate that cannot be evaluated fails."""
    gates: list[GateResult] = []

    missing = missing_fields(packet)
    gates.append(
        GateResult(
            "completeness",
            not missing,
            "complete" if not missing else f"missing: {', '.join(missing)}",
        )
    )
    if missing:
        # Fail closed: later gates cannot be evaluated against an
        # incomplete packet, so they fail rather than being skipped.
        for name in ("evidence", "brand_claims", "governance_tier"):
            gates.append(GateResult(name, False, "not evaluated: packet incomplete"))
        return gates

    evidence = packet["evidence"]
    has_evidence = isinstance(evidence, list) and len(evidence) > 0
    confident_enough = float(packet["confidence"]) >= MIN_ADVANCE_CONFIDENCE
    escalated = bool(packet.get("assumption_escalated"))
    evidence_ok = has_evidence and (confident_enough or escalated)
    if not has_evidence:
        reason = "no evidence cited"
    elif not evidence_ok:
        reason = (
            f"confidence {packet['confidence']} < {MIN_ADVANCE_CONFIDENCE} and "
            "not escalated as an assumption-driven bet"
        )
    else:
        reason = "evidence cited"
    gates.append(GateResult("evidence", evidence_ok, reason))

    text = _packet_text(packet)
    banned_hits = [phrase for phrase in BANNED_PHRASES if phrase in text]
    approved_claims = {
        entry.get("statement")
        for entry in memory.get("compliance", {}).get("claims_library", [])
        if isinstance(entry, dict)
    }
    unapproved = [
        claim for claim in packet.get("claims", []) if claim not in approved_claims
    ]
    claims_ok = not banned_hits and not unapproved
    if banned_hits:
        reason = f"banned language: {', '.join(banned_hits)}"
    elif unapproved:
        reason = f"claims not in compliance.claims_library: {', '.join(unapproved)}"
    else:
        reason = "clean"
    gates.append(GateResult("brand_claims", claims_ok, reason))

    tier = packet["risk_tier"]
    gates.append(GateResult("governance_tier", True, f"routed as {tier}"))
    return gates


def evaluate(packet: dict[str, Any], memory: dict[str, Any]) -> Evaluation:
    gates = run_gates(packet, memory)
    complete = gates[0].passed
    score = priority_score(packet["scores"]) if complete else 0.0
    evaluation = Evaluation(
        packet_id=str(packet.get("id", "<missing id>")), priority_score=score
    )
    evaluation.gates = gates
    if all(gate.passed for gate in gates):
        evaluation.disposition = RISK_DISPOSITIONS[packet["risk_tier"]]
    else:
        evaluation.disposition = "stopped_missing_information"
    return evaluation


def rank_initiatives(
    packets: list[dict[str, Any]], memory: dict[str, Any]
) -> list[Evaluation]:
    """Evaluate every packet and rank by Priority Score, highest first."""
    evaluations = [evaluate(packet, memory) for packet in packets]
    evaluations.sort(key=lambda e: e.priority_score, reverse=True)
    return evaluations


def load_memory(path: Path = SHARED_MEMORY_PATH) -> dict[str, Any]:
    """Load and validate the shared memory store (fail-closed)."""
    document = json.loads(path.read_text(encoding="utf-8"))
    memory = document.get("memory")
    if not isinstance(memory, dict):
        raise ValueError("shared memory document missing 'memory' object")
    for section, keys in MEMORY_SCHEMA.items():
        block = memory.get(section)
        if not isinstance(block, dict):
            raise ValueError(f"shared memory missing section '{section}'")
        for key in keys:
            if not isinstance(block.get(key), list):
                raise ValueError(f"shared memory missing list '{section}.{key}'")
        unknown = set(block) - set(keys)
        if unknown:
            raise ValueError(
                f"shared memory has unknown keys in '{section}': {sorted(unknown)}"
            )
    unknown_sections = set(memory) - set(MEMORY_SCHEMA)
    if unknown_sections:
        raise ValueError(f"shared memory has unknown sections: {sorted(unknown_sections)}")
    return memory


def append_entry(
    document_path: Path, section: str, key: str, entry: dict[str, Any]
) -> None:
    """Append one entry to a memory list. Never removes or rewrites entries."""
    if key not in MEMORY_SCHEMA.get(section, ()):
        raise ValueError(f"'{section}.{key}' is not part of the memory schema")
    document = json.loads(document_path.read_text(encoding="utf-8"))
    memory = document["memory"]
    memory[section][key].append({**entry, "recorded_at": _timestamp()})
    document["updated_at"] = _timestamp()
    document_path.write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )


def self_check() -> dict[str, Any]:
    """Governance self-check: the engine must stop incomplete packets,
    block high-risk work, and keep the committed memory store valid."""
    memory = load_memory()

    complete_packet = {
        "id": "self-check-ok",
        "title": "Self-check initiative",
        "owner_bot": "ANALYTICS-10",
        "reasoning": "Engine self-verification.",
        "evidence": ["scripts/marketing_os_v2.py self_check"],
        "expected_outcome": "Gates and scoring behave as specified.",
        "success_metric": "self-check pass rate",
        "target": "100%",
        "next_action": "Report result.",
        "confidence": 95,
        "scores": {
            "revenue_impact": 50, "lead_quality": 50, "strategic_fit": 50,
            "speed_to_execute": 50, "confidence": 95,
        },
        "risk_tier": "low",
    }
    ok = evaluate(complete_packet, memory)

    incomplete = evaluate({"id": "self-check-incomplete"}, memory)
    high_risk = evaluate({**complete_packet, "id": "self-check-high", "risk_tier": "high"}, memory)

    checks = {
        "memory_store_valid": True,
        "complete_low_risk_auto_executes": ok.disposition == "auto_execute_and_log",
        "incomplete_packet_stopped": incomplete.disposition == "stopped_missing_information",
        "high_risk_blocked": high_risk.disposition == "blocked_pending_approval",
        "priority_score_weighted": priority_score(
            {k: 100 for k in PRIORITY_WEIGHTS}
        ) == 100.0,
    }
    return {
        "generated_at": _timestamp(),
        "checks": checks,
        "passed": all(checks.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Marketing OS v2 governance engine")
    sub = parser.add_subparsers(dest="command", required=True)

    rank = sub.add_parser("rank", help="score, gate, and rank initiative packets")
    rank.add_argument("packets", type=Path, help="JSON file: list of initiative packets")

    check = sub.add_parser("self-check", help="run the governance self-check")
    check.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args(argv)
    if args.command == "rank":
        memory = load_memory()
        packets = json.loads(args.packets.read_text(encoding="utf-8"))
        evaluations = rank_initiatives(packets, memory)
        print(json.dumps([e.to_dict() for e in evaluations], indent=2))
        return 0
    report = self_check()
    if args.as_json:
        print(json.dumps(report, indent=2))
    else:
        for name, passed in report["checks"].items():
            print(f"{'PASS' if passed else 'FAIL'}  {name}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
