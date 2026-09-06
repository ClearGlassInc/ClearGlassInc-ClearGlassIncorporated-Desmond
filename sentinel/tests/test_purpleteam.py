"""Tests for the SENTINEL purple-team detection-engineering engine."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.purpleteam import (
    Engagement,
    Outcome,
    PurpleTeamEngine,
    PurpleTeamError,
    Scenario,
    Stage,
    Tactic,
    Technique,
)

ENG = Engagement(name="Q3-owned-corp", authorization_ref="PT-AUTH-2026-09",
                 scope="owned corp endpoints + cloud", jurisdiction="US-CA")
T_PSH = Technique("T1059.001", "PowerShell", Tactic.EXECUTION)
T_DUMP = Technique("T1003", "OS Credential Dumping", Tactic.CRED_ACCESS)
SC_PSH = Scenario("Detect malicious PowerShell on owned endpoints", T_PSH,
                  ("EDR", "script-block-logs"), "alert within 10m")
SC_DUMP = Scenario("Detect LSASS access on owned endpoints", T_DUMP,
                   ("EDR",), "alert within 15m")


def test_engagement_requires_authorization():
    with pytest.raises(PurpleTeamError):
        PurpleTeamEngine(Engagement("x", authorization_ref="", scope="owned"))
    with pytest.raises(PurpleTeamError):
        PurpleTeamEngine(Engagement("x", authorization_ref="PT-1", scope=""))


def test_detected_scenario_scores_clean():
    e = PurpleTeamEngine(ENG)
    s = e.simulate(SC_PSH, outcome=Outcome.DETECTED, ttd_min=6)
    assert s.outcome is Outcome.DETECTED and s.gap is None
    assert e.metrics()["detection_rate"] == 1.0


def test_missed_then_tune_then_retest_improves():
    e = PurpleTeamEngine(ENG)
    s = e.simulate(SC_DUMP, outcome=Outcome.MISSED)
    assert s.gap and "T1003" in s.gap
    assert e.metrics()["detection_rate"] == 0.0
    e.tune(s, "Sigma: LSASS handle access by non-system process")
    assert s.stage is Stage.TUNED and s.detection_rule
    e.retest(s, outcome=Outcome.DETECTED, ttd_min=8)
    assert s.improved and s.stage is Stage.VERIFIED and s.gap is None
    m = e.metrics()
    assert m["detection_rate"] == 0.0 and m["post_tune_rate"] == 1.0


def test_mttd_and_coverage():
    e = PurpleTeamEngine(ENG)
    e.simulate(SC_PSH, outcome=Outcome.DETECTED, ttd_min=4)
    s = e.simulate(SC_DUMP, outcome=Outcome.MISSED)
    e.tune(s, "rule")
    e.retest(s, outcome=Outcome.DETECTED, ttd_min=10)
    m = e.metrics()
    assert m["mttd_min"] == 7.0                       # mean(4,10)
    assert m["coverage"][Tactic.EXECUTION.value] == 1.0
    assert m["coverage"][Tactic.CRED_ACCESS.value] == 1.0


def test_open_gap_persists_when_not_retested():
    e = PurpleTeamEngine(ENG)
    e.simulate(SC_DUMP, outcome=Outcome.MISSED)
    assert len(e.metrics()["open_gaps"]) == 1


def test_partial_counts_as_gap_until_detected():
    e = PurpleTeamEngine(ENG)
    s = e.simulate(SC_PSH, outcome=Outcome.PARTIAL, ttd_min=40)
    assert s.gap is not None
    assert e.metrics()["post_tune_rate"] == 0.0
    e.tune(s, "lower alert threshold")
    e.retest(s, outcome=Outcome.DETECTED, ttd_min=5)
    assert e.metrics()["post_tune_rate"] == 1.0


def test_report_and_audit_chain():
    e = PurpleTeamEngine(ENG)
    s = e.simulate(SC_DUMP, outcome=Outcome.MISSED)
    e.tune(s, "rule")
    e.retest(s, outcome=Outcome.DETECTED, ttd_min=9)
    r = e.report()
    assert r.post_tune_rate == 1.0 and r.audit_ref
    assert "detection after tuning" in r.top_line
    assert e.audit.verify() is True                  # tamper-evident log intact
