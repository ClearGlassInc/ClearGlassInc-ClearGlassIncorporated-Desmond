"""SENTINEL — purple-team detection-engineering engine (defensive).

Models the collaborative purple-team cycle as auditable, measurable state:

    scope → simulate technique → observe detection/response → score →
    tune detection → retest → verify improvement

DEFENSIVE ONLY. This module plans, tracks, and SCORES detection coverage for
the operator's OWNED, AUTHORIZED environment. It contains no exploit code and
performs no attacks — it records exercise outcomes and drives the
detection-engineering feedback loop (detection rate, MTTD, retest pass rate,
ATT&CK coverage). Every engagement requires a documented ``authorization_ref``
and ``scope`` — fail-closed otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from statistics import mean
from typing import Optional

from .audit import AuditLog


class Tactic(str, Enum):
    """MITRE ATT&CK tactics (for coverage mapping)."""
    RECON = "reconnaissance"
    INITIAL_ACCESS = "initial-access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIV_ESC = "privilege-escalation"
    DEFENSE_EVASION = "defense-evasion"
    CRED_ACCESS = "credential-access"
    DISCOVERY = "discovery"
    LATERAL = "lateral-movement"
    COLLECTION = "collection"
    EXFIL = "exfiltration"
    IMPACT = "impact"


class Outcome(str, Enum):
    DETECTED = "DETECTED"      # alerted within objective
    PARTIAL = "PARTIAL"        # logged but no alert / slow
    MISSED = "MISSED"          # no telemetry / no detection


class Stage(str, Enum):
    SCOPED = "SCOPED"
    SIMULATED = "SIMULATED"
    TUNED = "TUNED"
    RETESTED = "RETESTED"
    VERIFIED = "VERIFIED"      # retest improved the control
    CLOSED = "CLOSED"


class PurpleTeamError(Exception):
    """Raised when an engagement is not properly authorized/scoped (fail-closed)."""


@dataclass(frozen=True)
class Technique:
    attack_id: str             # e.g. "T1059.001"
    name: str
    tactic: Tactic


@dataclass(frozen=True)
class Scenario:
    objective: str             # clearly scoped objective
    technique: Technique
    log_sources: tuple[str, ...]   # telemetry expected to catch it (EDR, proxy, auth…)
    success_metric: str        # e.g. "alert within 10 min"


@dataclass(frozen=True)
class Engagement:
    name: str
    authorization_ref: str     # documented authorization (mandatory)
    scope: str                 # owned systems / environment in scope (mandatory)
    jurisdiction: Optional[str] = None


@dataclass
class StepResult:
    scenario: Scenario
    stage: Stage
    outcome: Outcome
    ttd_min: Optional[float]           # time-to-detect (minutes), None if missed
    detection_rule: Optional[str] = None
    gap: Optional[str] = None
    retest_outcome: Optional[Outcome] = None
    retest_ttd_min: Optional[float] = None
    audit_ref: str = ""

    @property
    def improved(self) -> bool:
        if self.retest_outcome is None:
            return False
        rank = {Outcome.MISSED: 0, Outcome.PARTIAL: 1, Outcome.DETECTED: 2}
        return rank[self.retest_outcome] > rank[self.outcome]


@dataclass
class Report:
    top_line: str
    detection_rate: float
    post_tune_rate: float
    mttd_min: Optional[float]
    coverage: dict[str, float]
    open_gaps: list[str] = field(default_factory=list)
    audit_ref: str = ""


class PurpleTeamEngine:
    """Drives and scores a purple-team engagement. Defensive: outcomes only."""

    def __init__(self, engagement: Engagement, audit: Optional[AuditLog] = None) -> None:
        if not (engagement.authorization_ref or "").strip():
            raise PurpleTeamError("engagement requires documented authorization_ref (fail-closed)")
        if not (engagement.scope or "").strip():
            raise PurpleTeamError("engagement requires an explicit scope of owned systems (fail-closed)")
        self.engagement = engagement
        self.audit = audit or AuditLog()
        self.steps: list[StepResult] = []
        self._actor = f"purple/{engagement.name}"
        self.audit.record(actor=self._actor, action="scope",
                          detail={"authorization": engagement.authorization_ref, "scope": engagement.scope})

    # --- cycle ---------------------------------------------------------------
    def simulate(self, scenario: Scenario, *, outcome: Outcome,
                 ttd_min: Optional[float] = None, detection_rule: Optional[str] = None) -> StepResult:
        gap = None
        if outcome is not Outcome.DETECTED:
            gap = (f"{scenario.technique.attack_id} ({scenario.technique.tactic.value}): "
                   f"{'no telemetry/alert' if outcome is Outcome.MISSED else 'logged but no timely alert'} "
                   f"on {', '.join(scenario.log_sources)}")
        entry = self.audit.record(actor=self._actor, action="simulate",
                                  detail={"attack_id": scenario.technique.attack_id,
                                          "outcome": outcome.value, "ttd_min": ttd_min})
        step = StepResult(scenario, Stage.SIMULATED, outcome,
                          ttd_min if outcome is Outcome.DETECTED else (ttd_min if outcome is Outcome.PARTIAL else None),
                          detection_rule=detection_rule, gap=gap, audit_ref=entry.entry_hash[:12])
        self.steps.append(step)
        return step

    def tune(self, step: StepResult, detection_rule: str) -> StepResult:
        step.detection_rule = detection_rule
        step.stage = Stage.TUNED
        self.audit.record(actor=self._actor, action="tune",
                          detail={"attack_id": step.scenario.technique.attack_id, "rule": detection_rule})
        return step

    def retest(self, step: StepResult, *, outcome: Outcome, ttd_min: Optional[float] = None) -> StepResult:
        step.retest_outcome = outcome
        step.retest_ttd_min = ttd_min
        step.stage = Stage.VERIFIED if step.improved else Stage.RETESTED
        if step.improved and outcome is Outcome.DETECTED:
            step.gap = None
        self.audit.record(actor=self._actor, action="retest",
                          detail={"attack_id": step.scenario.technique.attack_id,
                                  "outcome": outcome.value, "improved": step.improved})
        return step

    # --- scoring -------------------------------------------------------------
    def _effective(self, s: StepResult) -> Outcome:
        return s.retest_outcome or s.outcome

    def metrics(self) -> dict:
        n = len(self.steps) or 1
        init_detected = sum(1 for s in self.steps if s.outcome is Outcome.DETECTED)
        post_detected = sum(1 for s in self.steps if self._effective(s) is Outcome.DETECTED)
        ttds = [s.retest_ttd_min if s.retest_ttd_min is not None else s.ttd_min
                for s in self.steps if (s.retest_ttd_min is not None or s.ttd_min is not None)]
        cov: dict[str, list[int]] = {}
        for s in self.steps:
            t = s.scenario.technique.tactic.value
            cov.setdefault(t, [0, 0])
            cov[t][1] += 1
            if self._effective(s) is Outcome.DETECTED:
                cov[t][0] += 1
        return {
            "scenarios": len(self.steps),
            "detection_rate": round(init_detected / n, 3),
            "post_tune_rate": round(post_detected / n, 3),
            "mttd_min": round(mean(ttds), 2) if ttds else None,
            "coverage": {k: round(v[0] / v[1], 3) for k, v in cov.items()},
            "open_gaps": [s.gap for s in self.steps if self._effective(s) is not Outcome.DETECTED and s.gap],
        }

    def report(self) -> Report:
        m = self.metrics()
        entry = self.audit.record(actor=self._actor, action="report", detail=m)
        improved = m["post_tune_rate"] - m["detection_rate"]
        top = (f"{int(m['post_tune_rate']*100)}% detection after tuning "
               f"(+{int(improved*100)} pts), MTTD {m['mttd_min']}m, "
               f"{len(m['open_gaps'])} open gap(s).")
        return Report(top, m["detection_rate"], m["post_tune_rate"], m["mttd_min"],
                      m["coverage"], m["open_gaps"], entry.entry_hash[:12])
