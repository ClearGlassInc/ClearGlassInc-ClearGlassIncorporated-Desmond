# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for agent_os/operator.py — the governed front door.

The operator turns a plain-language objective into real, policy-checked
execution. These tests pin the properties that make it safe to run unattended:
it never improvises, never writes without an explicit unlock, never executes
unless asked, and always leaves a verified audit chain.
"""
from __future__ import annotations

from pathlib import Path

from agent_os.operator import CAPABILITIES, Capability, Operator

REPO = Path(__file__).resolve().parents[1]


def _spy():
    """A runner that records calls instead of shelling out."""
    calls: list[list[str]] = []

    def run(argv, cwd):
        calls.append(list(argv))
        return 0, "ok"

    return calls, run


def _op(**kw) -> Operator:
    calls, run = _spy()
    op = Operator(REPO, runner=run, **kw)
    op._calls = calls  # type: ignore[attr-defined]
    return op


# --------------------------------------------------------------------------- #
# routing
# --------------------------------------------------------------------------- #
def test_objective_routes_to_the_right_capability():
    assert "site.audit" in [c.key for c in _op().match("audit the site")]
    assert "workflows.audit" in [c.key for c in _op().match("check the ci workflows")]


def test_unknown_objective_matches_nothing_and_is_reported_honestly():
    op = _op()
    res = op.handle("book me a flight to Tokyo and wire $5000", execute=True)
    assert res.unmatched is True
    assert res.matched == []
    assert res.executed == []                      # improvising is not an option
    assert "No registered capability" in res.summary
    assert op._calls == []                         # nothing was shelled out


def test_unmatched_objective_still_verifies_the_audit_chain():
    assert _op().handle("do something undefined").audit_verified is True


# --------------------------------------------------------------------------- #
# execution is opt-in
# --------------------------------------------------------------------------- #
def test_nothing_runs_unless_execute_is_requested():
    op = _op()
    res = op.handle("audit the site")              # execute defaults to False
    assert res.matched and res.executed == []
    assert op._calls == []
    assert "planned only" in res.summary


def test_read_only_capability_executes_when_asked():
    op = _op()
    res = op.handle("audit the site", execute=True)
    assert [e.key for e in res.executed] == ["site.audit"]
    assert res.executed[0].ok is True
    assert op._calls, "the capability's real command should have been invoked"


# --------------------------------------------------------------------------- #
# the write lock (two independent gates)
# --------------------------------------------------------------------------- #
def test_write_capability_is_refused_without_allow_writes():
    op = _op()
    res = op.handle("regenerate links", execute=True)
    refused = {r["key"] for r in res.refused}
    assert "links.refresh" in refused
    assert "links.refresh" not in [e.key for e in res.executed]
    assert all("internal_links.py" not in " ".join(c) or "--check" in c
               for c in op._calls), "the writing command must not have run"


def test_write_capability_runs_only_with_explicit_unlock():
    op = _op()
    res = op.handle("regenerate links", execute=True, allow_writes=True)
    assert "links.refresh" in [e.key for e in res.executed]
    assert res.refused == []


# --------------------------------------------------------------------------- #
# governance
# --------------------------------------------------------------------------- #
def test_capability_gated_by_governance_is_escalated_not_run():
    # An action name governance scores HIGH/CRITICAL must never auto-execute.
    gated = Capability(
        "danger.deploy", "Deploy to production", ("deploy to production",),
        "deploy_production", ("echo", "nope"),
    )
    op = Operator(REPO, capabilities=(gated,), runner=_spy()[1])
    res = op.handle("deploy to production", execute=True)
    assert [e["key"] for e in res.escalated] == ["danger.deploy"]
    assert res.executed == []


def test_unknown_action_fails_closed():
    # Unknown action names score 85 (HIGH) -> gated by construction.
    unknown = Capability(
        "mystery.thing", "Mystery", ("do the mystery",), "not_a_known_action",
        ("echo", "nope"),
    )
    op = Operator(REPO, capabilities=(unknown,), runner=_spy()[1])
    res = op.handle("do the mystery", execute=True)
    assert res.escalated and res.executed == []


def test_mission_report_and_audit_chain_accompany_every_run():
    res = _op().handle("audit the site", execute=True)
    assert res.audit_verified is True
    assert res.mission["objective"] == "audit the site"
    assert "validation_results" in res.mission


# --------------------------------------------------------------------------- #
# the unattended sweep
# --------------------------------------------------------------------------- #
def test_sweep_runs_every_read_only_capability():
    op = _op()
    res = op.sweep()
    ran = {e.key for e in res.executed}
    assert {c.key for c in CAPABILITIES if not c.writes} == ran
    assert res.audit_verified is True


def test_sweep_never_touches_a_writing_capability():
    op = _op()
    res = op.sweep()
    writers = {c.key for c in CAPABILITIES if c.writes}
    assert writers, "this test is meaningless if nothing writes"
    assert writers.isdisjoint({e.key for e in res.executed})
    assert writers.isdisjoint(set(res.matched))


# --------------------------------------------------------------------------- #
# the registry must stay real
# --------------------------------------------------------------------------- #
def test_every_registered_capability_points_at_a_file_that_exists():
    """The registry is a promise that these things actually run. Keep it true."""
    for cap in CAPABILITIES:
        targets = [a for a in cap.command
                   if a.endswith(".py") and not a.startswith("-")]
        for t in targets:
            assert (REPO / t).exists(), f"{cap.key} points at missing {t}"


def test_capabilities_that_write_are_marked_and_gated():
    for cap in CAPABILITIES:
        if cap.writes:
            # a writing capability must never be scored as a trivially-auto read
            assert cap.action != "read_metrics"
