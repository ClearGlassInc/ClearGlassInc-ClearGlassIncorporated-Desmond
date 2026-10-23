# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The head agent and its task store.

These pin the properties that make delegation safe to leave running: a task
runs at most once at a time, nothing writes without a human decision, a
failure stops what depended on it, retries are bounded and only for
interruptions, a cancel stops running work, workers cannot delegate, and the
history cannot be edited without the chain saying so.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agent_os.agents import AGENTS, HEAD_CAPABILITIES, AgentSpec, tool_of, validate_registry
from agent_os.head import HeadAgent, RunRequest, RunResult, subprocess_runner
from agent_os.planning import CycleError
from agent_os.tasks import (
    DelegationError,
    InvalidTransition,
    TaskSpec,
    TaskStatus,
    TaskStore,
    mission_status,
)

REPO = Path(__file__).resolve().parents[1]
S = TaskStatus


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


def runner_returning(stdout: str = "ok", code: int = 0, outcome: str = "completed", calls=None):
    def run(request: RunRequest) -> RunResult:
        if calls is not None:
            calls.append(request)
        return RunResult(code, stdout, "", 5, outcome)
    return run


def spec(cap: str = "links.check", agent: str = "verification", **kw) -> TaskSpec:
    return TaskSpec(capability=cap, assigned_agent=agent, objective=cap,
                    timeout_seconds=kw.pop("timeout_seconds", 10), max_attempts=kw.pop("max_attempts", 2), **kw)


def claim(store: TaskStore, worker: str = "w1"):
    return store.claim_next(worker, lease_seconds=30, agent_limits={a.key: 1 for a in AGENTS}, global_limit=4)


@pytest.fixture()
def clock() -> Clock:
    return Clock()


@pytest.fixture()
def store(tmp_path, clock) -> TaskStore:
    return TaskStore(tmp_path / "tasks.sqlite3", clock=clock)


# --------------------------------------------------------------------------- contract
def test_a_task_carries_every_contract_field(store):
    cid, _ = store.create_mission("x", requested_by="t", specs=[spec()], plan={})
    task = store.get_mission(cid)["tasks"][0]
    for name in ("task_id", "parent_task_id", "correlation_id", "assigned_agent", "objective", "input",
                 "dependencies", "status", "attempt", "deadline", "output", "error", "evidence",
                 "created_at", "updated_at", "started_at", "finished_at"):
        assert name in task, name
    assert task["status"] == "queued" and task["correlation_id"] == cid


def test_only_one_of_many_concurrent_workers_claims_a_task(store):
    store.create_mission("x", requested_by="t", specs=[spec()], plan={})
    claimed, barrier = [], threading.Barrier(8)

    def grab(n: int) -> None:
        barrier.wait()
        task = claim(store, f"w{n}")
        if task:
            claimed.append(task.lease_owner)

    threads = [threading.Thread(target=grab, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(claimed) == 1


def test_a_dependent_waits_and_is_blocked_when_its_upstream_fails(store):
    first = spec("links.refresh", "repository")
    second = spec(dependencies=(first.task_id,))
    third = spec("site.audit", dependencies=(second.task_id,))
    cid, _ = store.create_mission("x", requested_by="t", specs=[first, second, third], plan={})
    task = claim(store)
    assert task.task_id == first.task_id
    assert claim(store, "w2") is None  # the others are not runnable yet
    store.finish(task.task_id, "w1", S.FAILED, error="boom")
    states = {t["task_id"]: t["status"] for t in store.get_mission(cid)["tasks"]}
    assert states == {first.task_id: "failed", second.task_id: "blocked", third.task_id: "blocked"}
    assert store.get_mission(cid)["status"] == "failed"


def test_an_unknown_dependency_or_a_cycle_is_refused(store):
    with pytest.raises(KeyError):
        store.create_mission("x", requested_by="t", specs=[spec(dependencies=("tsk-missing",))], plan={})
    a = spec(task_id="tsk-aaaaaaaaaaaaaaaa", dependencies=("tsk-bbbbbbbbbbbbbbbb",))
    b = spec(task_id="tsk-bbbbbbbbbbbbbbbb", dependencies=("tsk-aaaaaaaaaaaaaaaa",))
    with pytest.raises(CycleError):
        store.create_mission("x", requested_by="t", specs=[a, b], plan={})


def test_workers_cannot_delegate_or_hand_work_to_the_head(store):
    with pytest.raises(DelegationError):
        store.create_mission("x", requested_by="t", specs=[spec(depth=2)], plan={})
    with pytest.raises(DelegationError):
        store.create_mission("x", requested_by="t", specs=[spec(agent="head")], plan={})
    with pytest.raises(DelegationError):
        store.create_mission("x", requested_by="t", specs=[spec(parent_task_id="tsk-elsewhere")], plan={})


def test_a_repeated_idempotency_key_returns_the_first_mission(store):
    first, created = store.create_mission("x", requested_by="t", specs=[spec()], plan={}, idempotency_key="k1")
    second, again = store.create_mission("x", requested_by="t", specs=[spec()], plan={}, idempotency_key="k1")
    assert (first, created, again) == (second, True, False)
    assert len(store.get_mission(first)["tasks"]) == 1


def test_only_the_lease_holder_can_record_an_outcome(store):
    store.create_mission("x", requested_by="t", specs=[spec()], plan={})
    task = claim(store)
    with pytest.raises(InvalidTransition):
        store.finish(task.task_id, "someone-else", S.SUCCEEDED)
    store.finish(task.task_id, "w1", S.SUCCEEDED)
    with pytest.raises(InvalidTransition):
        store.finish(task.task_id, "w1", S.FAILED)  # settled is final


def test_an_expired_lease_is_requeued_then_failed_when_attempts_run_out(store, clock):
    store.create_mission("x", requested_by="t", specs=[spec(max_attempts=2)], plan={})
    task = claim(store)
    clock.advance(31)
    assert store.recover_expired() == [task.task_id]
    again = claim(store, "w2")
    assert again.task_id == task.task_id and again.attempt == 2
    clock.advance(31)
    store.recover_expired()
    final = store.get_task(task.task_id)
    assert final.status is S.FAILED and "last of 2 attempts" in final.error


def test_a_task_whose_deadline_passed_fails_instead_of_starting_late(store, clock):
    first = spec(timeout_seconds=1, max_attempts=1)
    later = spec(dependencies=(first.task_id,))
    cid, _ = store.create_mission("x", requested_by="t", specs=[first, later], plan={})
    clock.advance(3600)
    assert claim(store) is None
    states = [t["status"] for t in store.get_mission(cid)["tasks"]]
    assert sorted(states) == ["blocked", "failed"]


def test_one_writer_per_work_tree_and_agent_limits_hold(store):
    store.create_mission("x", requested_by="t", plan={}, specs=[
        spec("links.refresh", "repository", resource="worktree"),
        spec("data.ieso.refresh", "integration", resource="worktree"),
        spec("site.audit"), spec("links.check"),
    ])
    running = [claim(store, f"w{n}") for n in range(4)]
    started = [t.capability for t in running if t]
    assert len([c for c in started if c.endswith("refresh")]) == 1  # same resource
    assert len([c for c in started if c in ("site.audit", "links.check")]) == 1  # verification limit 1 here


def test_rejecting_a_gated_task_cancels_it_and_blocks_its_dependents(store):
    gated = spec("links.refresh", "repository", gated=True)
    after = spec(dependencies=(gated.task_id,))
    cid, _ = store.create_mission("x", requested_by="t", specs=[gated, after], plan={})
    assert store.get_task(gated.task_id).deadline is None  # the clock starts at approval
    store.decide(gated.task_id, approver="owner", approve=False, reason="not now")
    assert store.get_task(gated.task_id).status is S.CANCELLED
    assert store.get_task(after.task_id).status is S.BLOCKED
    with pytest.raises(InvalidTransition):
        store.decide(gated.task_id, approver="owner", approve=True, reason="changed my mind")


def test_the_event_log_is_append_only_and_tampering_breaks_the_chain(store):
    cid, _ = store.create_mission("x", requested_by="t", specs=[spec()], plan={})
    assert store.events(cid)["chain_verified"] is True
    conn = sqlite3.connect(store.path)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE events SET payload = '{}' WHERE idx = 0")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM events")
    conn.execute("DROP TRIGGER events_no_update")  # an attacker with file access
    conn.execute("UPDATE events SET payload = ? WHERE idx = 0", (json.dumps({"objective": "edited"}),))
    conn.commit()
    conn.close()
    verdict = store.events(cid)
    assert verdict["chain_verified"] is False and verdict["first_bad_index"] == 0


def test_mission_status_reports_the_least_finished_state():
    def t(status, task_id="a", deps=()):
        return type("T", (), {"status": status, "task_id": task_id, "dependencies": list(deps)})()
    assert mission_status([], unmatched=True) == "unmatched"
    assert mission_status([t(S.SUCCEEDED), t(S.RUNNING)], unmatched=False) == "running"
    assert mission_status([t(S.SUCCEEDED), t(S.WAITING_FOR_APPROVAL)], unmatched=False) == "waiting_for_approval"
    assert mission_status([t(S.SUCCEEDED), t(S.CANCELLED)], unmatched=False) == "cancelled"
    assert mission_status([t(S.SUCCEEDED)], unmatched=False) == "succeeded"
    behind_approval = [t(S.WAITING_FOR_APPROVAL, "gate"), t(S.QUEUED, "check", deps=("gate",))]
    assert mission_status(behind_approval, unmatched=False) == "waiting_for_approval"
    assert mission_status([t(S.WAITING_FOR_APPROVAL, "gate"), t(S.QUEUED, "free")], unmatched=False) == "queued"


# --------------------------------------------------------------------------- registry
def test_the_shipped_registry_validates_and_every_tool_exists():
    assert validate_registry() == []
    for cap in HEAD_CAPABILITIES:
        tool = tool_of(cap)
        if tool.startswith("script:"):
            assert (REPO / tool.split(":", 1)[1]).exists(), tool


def test_registry_validation_catches_each_unsafe_shape():
    read_only = AgentSpec("ro", "ro", "", ("links.refresh",), ("script:tools/internal_links.py",), "",
                          10, 1, 1, "", "")
    assert any("writes but the agent is read-only" in p for p in validate_registry((read_only,), HEAD_CAPABILITIES))
    no_tool = AgentSpec("x", "x", "", ("links.check",), (), "", 10, 1, 1, "", "")
    assert any("not allowed" in p for p in validate_registry((no_tool,), HEAD_CAPABILITIES))
    assert any("no agent owns" in p for p in validate_registry(AGENTS[:1], HEAD_CAPABILITIES))
    with pytest.raises(ValueError, match="unsafe"):
        HeadAgent(TaskStore(":memory:"), agents=(read_only,))


# --------------------------------------------------------------------------- head agent
@pytest.fixture()
def head_factory(store):
    def make(runner=None, **kw) -> HeadAgent:
        return HeadAgent(store, root=REPO, runner=runner or runner_returning(), **kw)
    return make


def test_an_objective_nothing_matches_creates_no_work(head_factory):
    calls: list = []
    head = head_factory(runner_returning(calls=calls))
    mission = head.plan("negotiate a lease for the office", requested_by="t")
    assert mission["status"] == "unmatched" and mission["tasks"] == []
    assert head.work_once("w1") is None and calls == []


def test_writes_wait_for_approval_and_checks_run_after_changes(head_factory):
    head = head_factory()
    mission = head.plan("regenerate links then link check, and is it ready to deploy", requested_by="t")
    by_cap = {t["capability"]: t for t in mission["tasks"]}
    assert by_cap["links.refresh"]["status"] == "waiting_for_approval"
    assert by_cap["links.check"]["dependencies"] == [by_cap["links.refresh"]["task_id"]]
    others = {t["task_id"] for t in mission["tasks"] if t["capability"] != "deploy.readiness"}
    assert set(by_cap["deploy.readiness"]["dependencies"]) == others
    assert mission["plan"]["gated"] == ["links.refresh"]


def test_a_mission_is_bounded(head_factory):
    head = head_factory(max_tasks=2)
    mission = head.plan("audit everything: links, workflows, secrets, security, freshness", requested_by="t")
    assert len(mission["tasks"]) == 2 and mission["plan"]["truncated"] is True


def test_validated_output_succeeds_with_evidence(head_factory):
    head = head_factory(runner_returning(json.dumps({"clean": True, "findings": []})))
    mission = head.plan("find leaked credentials", requested_by="t")
    done = head.work_once("w1")
    assert done["status"] == "succeeded" and done["output"]["json"] == {"clean": True, "findings": []}
    assert "validation: passed" in done["evidence"]
    assert any(e.startswith("stdout_sha256: ") for e in done["evidence"])
    assert head.store.get_mission(mission["correlation_id"])["status"] == "succeeded"


def test_output_that_fails_validation_fails_the_task(head_factory):
    head = head_factory(runner_returning("all good, trust me"))
    head.plan("find leaked credentials", requested_by="t")
    done = head.work_once("w1")
    assert done["status"] == "failed" and "expected JSON" in done["error"]


def test_a_failing_check_is_a_finding_and_is_not_retried(head_factory):
    head = head_factory(runner_returning("2 broken links", code=1))
    head.plan("check internal links", requested_by="t")
    done = head.work_once("w1")
    assert (done["status"], done["attempt"], done["error"]) == ("failed", 1, "exit code 1")
    assert head.work_once("w1") is None


def test_a_timeout_is_retried_with_backoff_until_the_budget_is_spent(head_factory, clock):
    head = head_factory(runner_returning("", code=124, outcome="timeout"))
    head.plan("check internal links", requested_by="t")
    first = head.work_once("w1")
    assert first["status"] == "queued" and first["not_before"] is not None
    assert head.work_once("w1") is None  # still backing off
    clock.advance(5)
    second = head.work_once("w1")
    assert second["status"] == "failed" and "attempt budget of 2 spent" in second["error"]


def test_cancelling_a_mission_stops_its_running_command(head_factory, store):
    seen: list[str] = []

    def slow(request: RunRequest) -> RunResult:
        store.cancel_mission(store.list_missions()[0]["correlation_id"], by="test")
        for _ in range(100):
            reason = request.should_stop()
            if reason:
                seen.append(reason)
                return RunResult(-15, "", "", 10, reason)
            time.sleep(0.05)
        return RunResult(0, "finished anyway", "", 5000, "completed")

    head = head_factory(slow, lease_seconds=3)
    head.plan("check internal links", requested_by="t")
    done = head.work_once("w1")
    assert seen == ["cancelled"] and done["status"] == "cancelled"


def test_a_task_routed_to_the_wrong_agent_fails_the_permission_check(head_factory, store):
    calls: list = []
    head = head_factory(runner_returning(calls=calls))
    store.create_mission("x", requested_by="t", specs=[spec("security.secrets", "deployment")], plan={})
    done = head.work_once("w1")
    assert done["status"] == "failed" and "permission" in done["error"] and calls == []


def test_children_never_inherit_credentials(head_factory):
    calls: list = []
    env = {"PATH": "/usr/bin", "AGENT_OS_API_TOKEN": "x" * 30, "STRIPE_SECRET_KEY": "sk_live_" + "a" * 24,
           "GITHUB_TOKEN": "ghp_" + "b" * 36}
    head = head_factory(runner_returning(calls=calls), env=env)
    head.plan("check internal links", requested_by="t")
    head.work_once("w1")
    assert dict(calls[0].env) == {"PATH": "/usr/bin"}


def test_credentials_in_output_are_redacted_before_storage(head_factory):
    token = "operator-token-" + "z" * 20
    leaked = f"key sk_live_{'a' * 24} and {token} and Bearer abcdefghijklmnop"
    head = head_factory(runner_returning(leaked, code=1), secrets=(token,))
    head.plan("check internal links", requested_by="t")
    done = head.work_once("w1")
    stored = json.dumps(head.store.get_mission(done["correlation_id"]))
    assert "sk_live_" not in stored and token not in stored and "abcdefghijklmnop" not in stored
    assert "[REDACTED]" in done["output"]["stdout"]


def test_a_real_capability_runs_end_to_end(store):
    """No fakes: plan, claim, subprocess, validate, record."""
    head = HeadAgent(store, root=REPO)
    mission = head.plan("check data freshness", requested_by="t")
    done = head.work_once("real")
    assert done["status"] == "succeeded", done["error"]
    report = done["output"]["json"]
    assert report["schema"] == "clearglass.agent_os.freshness/1" and report["sources"]
    assert head.store.get_mission(mission["correlation_id"])["status"] == "succeeded"
    assert head.store.events(mission["correlation_id"])["chain_verified"] is True


# --------------------------------------------------------------------------- the subprocess runner
def _request(code: str, timeout: float, stop=lambda: None) -> RunRequest:
    return RunRequest((sys.executable, "-c", code), REPO, {"PATH": "/usr/bin:/bin"}, timeout, stop)


def test_the_runner_kills_a_command_that_overruns():
    started = time.monotonic()
    result = subprocess_runner(_request("import time; time.sleep(30)", 0.5))
    assert result.outcome == "timeout" and result.exit_code == 124
    assert time.monotonic() - started < 10


def test_the_runner_stops_a_command_when_asked():
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return "cancelled" if calls["n"] > 2 else None

    result = subprocess_runner(_request("import time; time.sleep(30)", 60, stop))
    assert result.outcome == "cancelled"


def test_the_runner_reports_a_missing_program_without_raising():
    result = subprocess_runner(RunRequest(("/nonexistent/tool",), REPO, {}, 5, lambda: None))
    assert (result.exit_code, result.outcome) == (127, "error")
