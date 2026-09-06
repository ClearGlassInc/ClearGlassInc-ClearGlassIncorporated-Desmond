# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""STEGOFORGE self-improving orchestration prototype for ClearGlassInc Artemis.

Production-oriented Python skeleton that demonstrates:
- event triage and enrichment
- policy-constrained recommendation
- human approval gate
- outcome capture and self-improvement proposal generation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from statistics import mean
from typing import Any


class Stage(str, Enum):
    TRIAGE = "TRIAGE"
    ENRICH = "ENRICH"
    RECOMMEND = "RECOMMEND"
    WAIT_APPROVAL = "WAIT_APPROVAL"
    EXECUTE = "EXECUTE"
    CLOSED = "CLOSED"


@dataclass(slots=True)
class Principal:
    user_id: str
    missions: set[str]
    coalition_domain: str
    clearance: str


@dataclass(slots=True)
class Event:
    event_id: str
    mission_id: str
    coalition_domain: str
    payload: dict[str, Any]
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class Recommendation:
    recommendation_id: str
    course_of_action: str
    confidence: float
    risk_reduction: float
    requires_commander_approval: bool


@dataclass(slots=True)
class RunRecord:
    run_id: str
    event_id: str
    stage: Stage
    recommendations: list[Recommendation] = field(default_factory=list)
    approved_actions: list[str] = field(default_factory=list)
    rejected_actions: list[str] = field(default_factory=list)
    outcome: dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    def assert_ingest(self, principal: Principal, event: Event) -> None:
        if event.mission_id not in principal.missions:
            raise PermissionError("mission access denied")
        if event.coalition_domain != principal.coalition_domain:
            raise PermissionError("coalition boundary mismatch")


class TriageAgent:
    def score(self, event: Event) -> dict[str, Any]:
        signals = event.payload.get("signals", 0)
        severity = min(1.0, 0.35 + (signals * 0.1))
        duplicate = bool(event.payload.get("known_duplicate", False))
        return {"severity": round(severity, 3), "duplicate": duplicate}


class EnrichmentAgent:
    def expand(self, event: Event, triage: dict[str, Any]) -> dict[str, Any]:
        inferred_entities = event.payload.get("entities", [])
        confidence = min(0.99, 0.7 + (0.2 if triage["severity"] > 0.8 else 0.1))
        return {
            "entities": inferred_entities,
            "confidence": round(confidence, 3),
            "campaign": event.payload.get("campaign", "unknown"),
        }


class RecommendationAgent:
    def propose(self, event: Event, triage: dict[str, Any], enrich: dict[str, Any]) -> list[Recommendation]:
        base = triage["severity"]
        recs = [
            Recommendation(
                recommendation_id=f"{event.event_id}-coa-1",
                course_of_action="Isolate affected segment",
                confidence=round(min(0.99, base + 0.03), 3),
                risk_reduction=0.79,
                requires_commander_approval=False,
            ),
            Recommendation(
                recommendation_id=f"{event.event_id}-coa-2",
                course_of_action="Push detection signatures",
                confidence=round(min(0.99, base + 0.02), 3),
                risk_reduction=0.63,
                requires_commander_approval=False,
            ),
            Recommendation(
                recommendation_id=f"{event.event_id}-coa-3",
                course_of_action="Notify cross-coalition partner",
                confidence=round(min(0.99, base - 0.04), 3),
                risk_reduction=0.58,
                requires_commander_approval=True,
            ),
        ]
        if enrich["campaign"] == "unknown":
            recs.sort(key=lambda r: r.risk_reduction, reverse=True)
        return recs


class SelfImprovementEngine:
    def generate_proposal(self, runs: list[RunRecord]) -> dict[str, Any]:
        if not runs:
            return {"status": "no_data"}

        confidence_values = [rec.confidence for run in runs for rec in run.recommendations]
        commander_rejects = sum(
            1
            for run in runs
            for rec in run.recommendations
            if rec.requires_commander_approval and rec.course_of_action in run.rejected_actions
        )
        avg_conf = round(mean(confidence_values), 3) if confidence_values else 0.0

        proposal = {
            "proposal_id": sha256(f"{datetime.now(timezone.utc).isoformat()}:{len(runs)}".encode()).hexdigest()[:12],
            "avg_confidence": avg_conf,
            "commander_rejects": commander_rejects,
            "change_set": [
                "decrease routing weight for low-lineage external feeds by 0.10",
                "tighten recommendation threshold for cross-coalition actions from 0.70 to 0.78",
                "add evidence completeness check before proposing partner notification",
            ],
            "requires_human_approval": True,
        }
        return proposal


class StegoForgeSystem:
    def __init__(self) -> None:
        self.policy = PolicyEngine()
        self.triage = TriageAgent()
        self.enrichment = EnrichmentAgent()
        self.recommendation = RecommendationAgent()
        self.self_improver = SelfImprovementEngine()
        self.runs: list[RunRecord] = []

    def process_event(self, principal: Principal, event: Event) -> RunRecord:
        self.policy.assert_ingest(principal, event)
        run = RunRecord(run_id=f"run-{event.event_id}", event_id=event.event_id, stage=Stage.TRIAGE)

        triage = self.triage.score(event)
        if triage["duplicate"]:
            run.stage = Stage.CLOSED
            run.outcome = {"reason": "duplicate"}
            self.runs.append(run)
            return run

        run.stage = Stage.ENRICH
        enrich = self.enrichment.expand(event, triage)

        run.stage = Stage.RECOMMEND
        run.recommendations = self.recommendation.propose(event, triage, enrich)

        run.stage = Stage.WAIT_APPROVAL
        for rec in run.recommendations:
            if rec.requires_commander_approval:
                run.rejected_actions.append(rec.course_of_action)
            else:
                run.approved_actions.append(rec.course_of_action)

        run.stage = Stage.EXECUTE
        run.outcome = {
            "contained": True,
            "lateral_movement_detected": False,
            "analyst_trust": 0.93,
            "latency_ms": 640,
        }

        run.stage = Stage.CLOSED
        self.runs.append(run)
        return run

    def improvement_proposal(self) -> dict[str, Any]:
        return self.self_improver.generate_proposal(self.runs)


if __name__ == "__main__":
    system = StegoForgeSystem()
    principal = Principal(
        user_id="operator-7",
        missions={"mission-artemis-001"},
        coalition_domain="NATO-REL",
        clearance="SECRET",
    )
    event = Event(
        event_id="evt-9001",
        mission_id="mission-artemis-001",
        coalition_domain="NATO-REL",
        payload={
            "signals": 7,
            "entities": ["host-22", "ioc-445", "campaign-azimuth"],
            "campaign": "azimuth",
        },
    )

    run = system.process_event(principal, event)
    print({"run_id": run.run_id, "approved": run.approved_actions, "rejected": run.rejected_actions})
    print(system.improvement_proposal())
