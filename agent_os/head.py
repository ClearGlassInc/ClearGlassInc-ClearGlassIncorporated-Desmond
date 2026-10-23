# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The head agent: objective in, delegated and verified work out.

``plan`` turns a plain-language objective into a bounded mission. It routes
the objective through the operator's capability registry (no match means no
mission, never an improvised action), assigns each capability to the one
worker agent registered for it, orders the tasks, scores each with the
governance gate, and persists the mission. Tasks that write, or that the gate
does not score LOW, start in ``waiting_for_approval``.

``work_once`` is one worker step: claim the next runnable task under a lease,
check the agent may use that tool, run it with a timeout, validate the output,
and record the result with its evidence. Cancellation, lease loss and shutdown
are checked while the command runs.

What keeps it bounded:

* at most ``max_tasks`` tasks per mission, and workers cannot delegate
  (:data:`agent_os.tasks.MAX_DEPTH`), so there is no recursive loop to run away;
* per-agent and global concurrency limits, and one writer per work tree;
* a timeout per attempt, a deadline per task, and an attempt budget — only a
  timeout or an interrupted run is retried, because a failing check is a
  finding and running it again changes nothing;
* child processes get an allow-listed environment, never the API tokens.

    python -m agent_os.head run "check data freshness"     # plan + work to completion
    python -m agent_os.head plan "run a security review"   # persist a mission only
    python -m agent_os.head work                           # process the queue
    python -m agent_os.head status <correlation_id>
    python -m agent_os.head approve <task_id> --approver NAME --reason TEXT
    python -m agent_os.head cancel <correlation_id>

Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agents import (
    AGENTS,
    HEAD_CAPABILITIES,
    SUMMARIZERS,
    VALIDATORS,
    AgentSpec,
    tool_of,
    validate_registry,
)
from .freshness import report as freshness_report
from .governance import RiskTier, score_action
from .operator import Capability, Operator
from .planning import Task as PlanTask
from .planning import plan_waves
from .redaction import redact
from .tasks import Task, TaskSpec, TaskStatus, TaskStore, parse_iso

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = _REPO_ROOT / ".agent_os" / "tasks.sqlite3"
MAX_OBJECTIVE = 500
MAX_STREAM_BYTES = 32_000
MAX_TASKS = 10
CANCEL_POLL_SECONDS = 2.0

#: What a child process may inherit. Everything else — API tokens, cloud
#: credentials, payment keys — stays in the server process.
CHILD_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR", "PYTHONIOENCODING",
             "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy",
             "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE")

#: Ordering rules: a task runs after the listed capabilities when the same
#: mission contains them. Verify after you change, report readiness last.
AFTER: dict[str, tuple[str, ...]] = {
    "data.freshness": ("data.ieso.refresh", "data.minerals.refresh"),
    "links.check": ("links.refresh",),
}
LAST = ("deploy.readiness",)

log = logging.getLogger("agent_os.head")


@dataclass(frozen=True)
class RunRequest:
    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]
    timeout: float
    should_stop: Callable[[], str | None]


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    #: completed | timeout | cancelled | lost | shutdown | error
    outcome: str


Runner = Callable[[RunRequest], RunResult]


def _stop_process(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (OSError, AttributeError):
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, AttributeError):
            proc.kill()


def subprocess_runner(request: RunRequest) -> RunResult:
    """Run argv in its own process group; stop it on timeout, cancel or shutdown."""
    started = time.monotonic()
    try:
        proc = subprocess.Popen(
            list(request.argv), cwd=request.cwd, env=dict(request.env), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
    except OSError as exc:
        return RunResult(127, "", f"could not execute: {exc}", 0, "error")
    outcome = "completed"
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=0.25)
            break
        except subprocess.TimeoutExpired:
            if time.monotonic() - started > request.timeout:
                outcome = "timeout"
            else:
                outcome = request.should_stop() or "completed"
            if outcome != "completed":
                _stop_process(proc)
                stdout, stderr = proc.communicate()
                break
    code = proc.returncode if outcome == "completed" else (124 if outcome == "timeout" else -15)
    return RunResult(code, stdout or "", stderr or "", int((time.monotonic() - started) * 1000), outcome)


def clean_objective(objective: object) -> str:
    if not isinstance(objective, str):
        raise ValueError("objective must be a string")
    text = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", objective).split())
    if not 3 <= len(text) <= MAX_OBJECTIVE:
        raise ValueError(f"objective must be 3-{MAX_OBJECTIVE} characters")
    return text


def _clip(text: str, secrets: tuple[str, ...]) -> tuple[str, bool]:
    clean = redact(text, literals=secrets)
    if len(clean) <= MAX_STREAM_BYTES:
        return clean, False
    return clean[:MAX_STREAM_BYTES] + "\n…[truncated]", True


class HeadAgent:
    def __init__(
        self,
        store: TaskStore,
        *,
        root: Path | str | None = None,
        agents: tuple[AgentSpec, ...] = AGENTS,
        capabilities: tuple[Capability, ...] = HEAD_CAPABILITIES,
        runner: Runner | None = None,
        lease_seconds: int = 30,
        global_concurrency: int = 2,
        max_tasks: int = MAX_TASKS,
        secrets: tuple[str, ...] = (),
        env: Mapping[str, str] | None = None,
    ) -> None:
        problems = validate_registry(agents, capabilities)
        if problems:
            raise ValueError("agent registry is unsafe: " + "; ".join(problems))
        self.store = store
        self.root = Path(root) if root is not None else _REPO_ROOT
        self.agents = {a.key: a for a in agents}
        self.capabilities = {c.key: c for c in capabilities}
        self.owner = {key: a for a in agents for key in a.capabilities}
        self.router = Operator(self.root, capabilities=capabilities)
        self.runner = runner or subprocess_runner
        self.lease_seconds = lease_seconds
        self.global_concurrency = global_concurrency
        self.max_tasks = max_tasks
        self.secrets = tuple(s for s in secrets if s)
        source = os.environ if env is None else env
        self.child_env = {k: source[k] for k in CHILD_ENV if k in source}
        self._shutdown_at: float | None = None

    # ------------------------------------------------------------------ planning
    def plan(self, objective: str, *, requested_by: str,
             idempotency_key: str | None = None) -> dict[str, Any]:
        text = clean_objective(objective)
        matched = self.router.match(text)
        truncated = len(matched) > self.max_tasks
        matched = matched[: self.max_tasks]

        specs: dict[str, TaskSpec] = {}
        for cap in matched:
            agent = self.owner[cap.key]
            assessment = score_action(cap.action, {"capability": cap.key, "writes": cap.writes},
                                      confidence=0.9, has_evidence=True)
            specs[cap.key] = TaskSpec(
                capability=cap.key,
                assigned_agent=agent.key,
                objective=f"{cap.title} — for: {text}",
                input={"capability": cap.key},
                timeout_seconds=agent.timeout_seconds,
                max_attempts=agent.max_attempts,
                gated=cap.writes or assessment.requires_approval or assessment.tier is not RiskTier.LOW,
                resource="worktree" if cap.writes else None,
                risk=assessment.to_dict(),
            )

        deps: dict[str, tuple[str, ...]] = {}
        for key in specs:
            before = AFTER.get(key, ())
            if key in LAST:
                before = tuple(k for k in specs if k not in LAST)
            deps[key] = tuple(specs[k].task_id for k in before if k in specs)

        # Deadlines along the critical path, so waiting on slow work is not expiry.
        by_id = {s.task_id: k for k, s in specs.items()}
        waves = plan_waves([PlanTask(s.task_id, deps[k]) for k, s in specs.items()])
        budget: dict[str, int] = {}
        for wave in waves:
            for task_id in wave:
                key = by_id[task_id]
                upstream = max((budget[d] for d in deps[key]), default=0)
                budget[task_id] = specs[key].own_budget + upstream
        final = [
            TaskSpec(**{**spec.__dict__, "dependencies": deps[key], "budget_seconds": budget[spec.task_id]})
            for key, spec in specs.items()
        ]

        plan = {
            "unmatched": not matched,
            "truncated": truncated,
            "waves": [[by_id[t] for t in wave] for wave in waves],
            "assignments": {s.capability: s.assigned_agent for s in final},
            "gated": [s.capability for s in final if s.gated],
            "note": ("No registered capability matches this objective; nothing was improvised."
                     if not matched else
                     "Gated tasks wait for a human decision; everything else runs in wave order."),
        }
        correlation_id, created = self.store.create_mission(
            text, requested_by=requested_by, specs=final, plan=plan,
            idempotency_key=idempotency_key)
        self._log("mission_planned", correlation_id=correlation_id, created=created,
                  tasks=len(final), gated=len(plan["gated"]))
        mission = self.store.get_mission(correlation_id)
        assert mission is not None
        return {**mission, "created": created}

    # ------------------------------------------------------------------ execution
    def begin_shutdown(self, grace_seconds: float) -> None:
        """Running commands get ``grace_seconds`` to finish, then are stopped and re-queued."""
        self._shutdown_at = time.monotonic() + grace_seconds

    def work_once(self, worker_id: str) -> dict[str, Any] | None:
        for task_id in self.store.recover_expired():
            self._log("lease_recovered", task_id=task_id)
        task = self.store.claim_next(
            worker_id, lease_seconds=self.lease_seconds,
            agent_limits={a.key: a.max_concurrency for a in self.agents.values()},
            global_limit=self.global_concurrency)
        if task is None:
            return None
        self._log("task_started", correlation_id=task.correlation_id, task_id=task.task_id,
                  agent=task.assigned_agent, capability=task.capability, attempt=task.attempt)

        cap = self.capabilities.get(task.capability)
        agent = self.agents.get(task.assigned_agent)
        if (cap is None or agent is None or cap.key not in agent.capabilities
                or tool_of(cap) not in agent.allowed_tools):
            done = self.store.finish(task.task_id, worker_id, TaskStatus.FAILED,
                                     error="tool permission check failed: capability not allowed for this agent",
                                     evidence=[f"agent={task.assigned_agent}", f"capability={task.capability}"])
            return self._finished(done)

        deadline = parse_iso(task.deadline)
        remaining = (deadline - self.store.clock()).total_seconds() if deadline else task.timeout_seconds
        timeout = max(1.0, min(float(task.timeout_seconds), remaining))
        last_renew = time.monotonic()

        def should_stop() -> str | None:
            nonlocal last_renew
            if self._shutdown_at is not None and time.monotonic() >= self._shutdown_at:
                return "shutdown"
            # Renewing also reads the cancel flag, so check often: a cancel should
            # stop a command within seconds, not at the next lease boundary.
            if time.monotonic() - last_renew >= min(self.lease_seconds / 3, CANCEL_POLL_SECONDS):
                last_renew = time.monotonic()
                owned, cancel = self.store.renew_lease(task.task_id, worker_id, self.lease_seconds)
                if not owned:
                    return "lost"
                if cancel:
                    return "cancelled"
            return None

        cwd = self.router._cwd_for(cap)
        result = self.runner(RunRequest(cap.command, cwd, self.child_env, timeout, should_stop))
        return self._record(task, worker_id, cap, cwd, result)

    def _record(self, task: Task, worker_id: str, cap: Capability, cwd: Path,
                result: RunResult) -> dict[str, Any] | None:
        stdout, cut_out = _clip(result.stdout, self.secrets)
        stderr, cut_err = _clip(result.stderr, self.secrets)
        output: dict[str, Any] = {"exit_code": result.exit_code, "stdout": stdout, "stderr": stderr,
                                  "duration_ms": result.duration_ms, "truncated": cut_out or cut_err}
        argv = " ".join("python" if a == sys.executable else a for a in cap.command)
        evidence = [
            f"command: {argv}",
            f"cwd: {cwd.relative_to(self.root) if cwd.is_relative_to(self.root) else cwd}",
            f"exit_code: {result.exit_code}",
            f"outcome: {result.outcome}",
            f"stdout_sha256: {hashlib.sha256(result.stdout.encode()).hexdigest()}",
            f"duration_ms: {result.duration_ms}",
            f"worker: {worker_id}",
            f"attempt: {task.attempt}/{task.max_attempts}",
        ]
        status, error, retry = TaskStatus.SUCCEEDED, None, None
        if result.outcome == "lost":
            self._log("lease_lost", task_id=task.task_id)
            return None  # another worker owns it now; this one must not write
        if result.outcome == "cancelled":
            status, error = TaskStatus.CANCELLED, "cancelled while running"
        elif result.outcome in ("timeout", "shutdown"):
            status, retry = TaskStatus.QUEUED, min(60.0, 2.0 ** task.attempt)
            error = (f"timed out after {result.duration_ms // 1000}s" if result.outcome == "timeout"
                     else "interrupted by shutdown")
        elif result.outcome == "error":
            status, error = TaskStatus.FAILED, stderr or "could not execute"
        else:
            problems: list[str] = []
            validator = VALIDATORS.get(cap.key)
            if validator is not None:
                try:
                    document = json.loads(redact(result.stdout, literals=self.secrets))
                except ValueError:
                    problems.append("expected JSON output and got something else")
                else:
                    problems.extend(validator(document))
                    if not problems and len(json.dumps(document)) > MAX_STREAM_BYTES:
                        summarize = SUMMARIZERS.get(cap.key)
                        document = summarize(document) if summarize else None
                        output["json_summarized"] = True
                    output["json"] = document
            if result.exit_code != 0:
                problems.insert(0, f"exit code {result.exit_code}")
            if problems:
                status, error = TaskStatus.FAILED, "; ".join(problems)
            evidence.append("validation: " + ("passed" if not problems else "; ".join(problems)))
        done = self.store.finish(task.task_id, worker_id, status, output=output, error=error,
                                 evidence=evidence, retry_in_seconds=retry)
        return self._finished(done)

    def _finished(self, task: Task) -> dict[str, Any]:
        self._log("task_finished", correlation_id=task.correlation_id, task_id=task.task_id,
                  status=task.status.value, attempt=task.attempt, error=task.error)
        return task.to_dict()

    def work(self, worker_id: str, stop: threading.Event, *, idle_seconds: float = 1.0,
             heartbeat: Callable[[], None] | None = None) -> None:
        while not stop.is_set():
            if heartbeat:
                heartbeat()
            try:
                if self.work_once(worker_id) is None:
                    stop.wait(idle_seconds)
            except Exception:  # noqa: BLE001 - a worker must outlive one bad task
                log.exception("worker %s step failed", worker_id)
                stop.wait(idle_seconds)

    def run_until_settled(self, correlation_id: str, *, worker_id: str = "cli",
                          timeout_seconds: float = 3600) -> dict[str, Any]:
        """Work this mission in-process until nothing more can happen without a human."""
        limit = time.monotonic() + timeout_seconds
        while time.monotonic() < limit:
            mission = self.store.get_mission(correlation_id)
            assert mission is not None
            if mission["status"] not in ("queued", "running"):
                return mission
            if self.work_once(worker_id) is None:
                time.sleep(0.5)
        return self.store.get_mission(correlation_id) or {}

    # ------------------------------------------------------------------ control + views
    def cancel(self, correlation_id: str, *, by: str) -> dict[str, int]:
        counts = self.store.cancel_mission(correlation_id, by=by)
        self._log("mission_cancel_requested", correlation_id=correlation_id, **counts)
        return counts

    def decide(self, task_id: str, *, approver: str, approve: bool, reason: str) -> dict[str, Any]:
        task = self.store.decide(task_id, approver=approver, approve=approve, reason=reason)
        self._log("approval_decision", correlation_id=task.correlation_id, task_id=task_id,
                  decision="approved" if approve else "rejected", approver=approver)
        return task.to_dict()

    def metrics(self) -> dict[str, Any]:
        fresh = freshness_report(self.root)
        return {**self.store.metrics(),
                "data_freshness": fresh["summary"],
                "data_sources": [{k: s.get(k) for k in ("id", "feed", "state", "age_hours", "last_success_utc")}
                                 for s in fresh["sources"]]}

    def registry(self) -> list[dict[str, Any]]:
        return [{**a.to_dict(),
                 "capability_detail": [self.capabilities[k].to_dict() | {"tool": tool_of(self.capabilities[k])}
                                       for k in a.capabilities]}
                for a in self.agents.values()]

    def _log(self, event: str, **fields: Any) -> None:
        line = json.dumps({"event": event, **fields}, default=str, sort_keys=True)
        log.info(redact(line, literals=self.secrets))


# ---------------------------------------------------------------------- CLI
def _store(path: str | None) -> TaskStore:
    return TaskStore(path or os.environ.get("AGENT_OS_DB") or DEFAULT_DB)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agent_os.head", description="Governed head agent.")
    ap.add_argument("--db", help="task database (default: $AGENT_OS_DB or .agent_os/tasks.sqlite3)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "plan"):
        p = sub.add_parser(name)
        p.add_argument("objective", nargs="+")
        p.add_argument("--key", help="idempotency key")
    p = sub.add_parser("work")
    p.add_argument("--once", action="store_true")
    p.add_argument("--worker", default=f"cli-{os.getpid()}")
    for name in ("status", "events", "cancel"):
        sub.add_parser(name).add_argument("correlation_id")
    p = sub.add_parser("approve")
    p.add_argument("task_id")
    p.add_argument("--approver", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--reject", action="store_true")
    sub.add_parser("agents")
    sub.add_parser("metrics")
    ns = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    head = HeadAgent(_store(ns.db))
    out: Any
    if ns.cmd in ("run", "plan"):
        out = head.plan(" ".join(ns.objective), requested_by=f"cli:{os.environ.get('USER', 'local')}",
                        idempotency_key=ns.key)
        if ns.cmd == "run":
            out = head.run_until_settled(out["correlation_id"])
    elif ns.cmd == "work":
        if ns.once:
            out = head.work_once(ns.worker)
        else:
            stop = threading.Event()
            signal.signal(signal.SIGTERM, lambda *_: stop.set())
            try:
                head.work(ns.worker, stop)
            except KeyboardInterrupt:
                stop.set()
            return 0
    elif ns.cmd == "status":
        out = head.store.get_mission(ns.correlation_id)
    elif ns.cmd == "events":
        out = head.store.events(ns.correlation_id)
    elif ns.cmd == "cancel":
        out = head.cancel(ns.correlation_id, by=f"cli:{os.environ.get('USER', 'local')}")
    elif ns.cmd == "approve":
        out = head.decide(ns.task_id, approver=ns.approver, approve=not ns.reject, reason=ns.reason)
    elif ns.cmd == "agents":
        out = head.registry()
    else:
        out = head.metrics()
    print(json.dumps(out, indent=2, default=str))
    if isinstance(out, dict) and out.get("status") in ("failed", "blocked", "unmatched"):
        return 1
    return 0 if out is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
