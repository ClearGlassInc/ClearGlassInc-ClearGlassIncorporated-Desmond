# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The shared task contract and its durable store.

Every unit of work the head agent hands to a worker agent is a row in a SQLite
database, so a mission survives a crash or a restart. The contract fields are
the ones the head agent and every worker agree on:

    task_id, parent_task_id, correlation_id, assigned_agent, objective, input,
    dependencies, status, attempt, deadline, output, error, evidence,
    created_at / updated_at / started_at / finished_at

States, and the only moves between them::

    waiting_for_approval --approve--> queued --claim--> running --> succeeded
             |                          |                 |   \\--> failed
             +--reject--> cancelled     +--> blocked      |    \\-> cancelled
                                        +--> failed       +--retry / lease lost--> queued
                                             (deadline)

``blocked`` means a dependency failed or was cancelled, so the task can never
run. It is settled, like the three terminal states.

Duplicate execution is prevented twice over. A claim runs inside
``BEGIN IMMEDIATE`` — one writer at a time across every process sharing the
file — and is itself a conditional ``UPDATE … WHERE status = 'queued'`` whose
row count proves the claim. A running task holds a lease; a worker that dies
lets the lease lapse and :meth:`TaskStore.recover_expired` re-queues the task
(within its attempt budget) for another worker.

The event log is append-only (SQLite triggers refuse UPDATE and DELETE) and
hash-chained per mission with the same digest as :mod:`agent_os.audit`, so
:meth:`TaskStore.events` can prove the history was not edited.

Stdlib only.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from .audit import GENESIS, AuditLedger, _digest
from .planning import Task as PlanTask
from .planning import plan_waves

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

#: The head agent is depth 0; the tasks it assigns are depth 1. A worker may
#: not delegate further, which is what rules out recursive delegation loops.
MAX_DEPTH = 1
HEAD = "head"


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(ISO_FORMAT)


def parse_iso(text: str | None) -> datetime | None:
    return datetime.strptime(text, ISO_FORMAT).replace(tzinfo=UTC) if text else None


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    BLOCKED = "blocked"


S = TaskStatus
SETTLED = frozenset({S.SUCCEEDED, S.FAILED, S.CANCELLED, S.BLOCKED})

TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    S.WAITING_FOR_APPROVAL: frozenset({S.QUEUED, S.CANCELLED, S.BLOCKED}),
    S.QUEUED: frozenset({S.RUNNING, S.CANCELLED, S.BLOCKED, S.FAILED}),
    S.RUNNING: frozenset({S.SUCCEEDED, S.FAILED, S.CANCELLED, S.QUEUED}),
    S.SUCCEEDED: frozenset(),
    S.FAILED: frozenset(),
    S.CANCELLED: frozenset(),
    S.BLOCKED: frozenset(),
}


class InvalidTransition(ValueError):
    """A state change the contract does not allow. Nothing was written."""


class DelegationError(ValueError):
    """A task tried to delegate past :data:`MAX_DEPTH`, or to the head itself."""


@dataclass(frozen=True)
class TaskSpec:
    """What the head agent asks the store to create."""

    capability: str
    assigned_agent: str
    objective: str
    timeout_seconds: int
    max_attempts: int
    input: dict[str, Any] = field(default_factory=dict)
    dependencies: tuple[str, ...] = ()
    gated: bool = False
    resource: str | None = None
    risk: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None
    depth: int = 1
    #: Seconds from queue time to deadline. The head agent sets it along the
    #: critical path, so a task waiting on slow upstream work does not expire
    #: before it could start. ``None`` means this task's own attempts only.
    budget_seconds: int | None = None
    task_id: str = field(default_factory=lambda: f"tsk-{uuid.uuid4().hex[:16]}")

    @property
    def own_budget(self) -> int:
        return own_budget(self.timeout_seconds, self.max_attempts)


def own_budget(timeout_seconds: int, max_attempts: int) -> int:
    """Room for every attempt plus backoff; past the deadline a task fails, not hangs."""
    return timeout_seconds * max_attempts * 2 + 60


@dataclass
class Task:
    task_id: str
    parent_task_id: str | None
    correlation_id: str
    assigned_agent: str
    capability: str
    objective: str
    input: dict[str, Any]
    dependencies: list[str]
    status: TaskStatus
    attempt: int
    max_attempts: int
    timeout_seconds: int
    budget_seconds: int
    deadline: str | None
    output: dict[str, Any] | None
    error: str | None
    evidence: list[str]
    risk: dict[str, Any]
    depth: int
    resource: str | None
    not_before: str | None
    lease_owner: str | None
    lease_expires_at: str | None
    cancel_requested: bool
    approved_by: str | None
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Task:
        return cls(
            task_id=row["task_id"],
            parent_task_id=row["parent_task_id"],
            correlation_id=row["correlation_id"],
            assigned_agent=row["assigned_agent"],
            capability=row["capability"],
            objective=row["objective"],
            input=json.loads(row["input"]),
            dependencies=json.loads(row["dependencies"]),
            status=TaskStatus(row["status"]),
            attempt=row["attempt"],
            max_attempts=row["max_attempts"],
            timeout_seconds=row["timeout_seconds"],
            budget_seconds=row["budget_seconds"],
            deadline=row["deadline"],
            output=json.loads(row["output"]) if row["output"] else None,
            error=row["error"],
            evidence=json.loads(row["evidence"]),
            risk=json.loads(row["risk"]),
            depth=row["depth"],
            resource=row["resource"],
            not_before=row["not_before"],
            lease_owner=row["lease_owner"],
            lease_expires_at=row["lease_expires_at"],
            cancel_requested=bool(row["cancel_requested"]),
            approved_by=row["approved_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )

    def to_dict(self) -> dict[str, Any]:
        row = dict(self.__dict__)
        row["status"] = self.status.value
        return row


_SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    correlation_id  TEXT PRIMARY KEY,
    objective       TEXT NOT NULL,
    requested_by    TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    created_at      TEXT NOT NULL,
    plan            TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    task_id          TEXT PRIMARY KEY,
    parent_task_id   TEXT,
    correlation_id   TEXT NOT NULL REFERENCES missions(correlation_id),
    assigned_agent   TEXT NOT NULL,
    capability       TEXT NOT NULL,
    objective        TEXT NOT NULL,
    input            TEXT NOT NULL,
    dependencies     TEXT NOT NULL,
    status           TEXT NOT NULL,
    attempt          INTEGER NOT NULL DEFAULT 0,
    max_attempts     INTEGER NOT NULL,
    timeout_seconds  INTEGER NOT NULL,
    budget_seconds   INTEGER NOT NULL,
    deadline         TEXT,
    output           TEXT,
    error            TEXT,
    evidence         TEXT NOT NULL DEFAULT '[]',
    risk             TEXT NOT NULL DEFAULT '{}',
    depth            INTEGER NOT NULL,
    resource         TEXT,
    not_before       TEXT,
    lease_owner      TEXT,
    lease_expires_at TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    approved_by      TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    started_at       TEXT,
    finished_at      TEXT
);
CREATE INDEX IF NOT EXISTS tasks_by_status ON tasks(status, created_at);
CREATE INDEX IF NOT EXISTS tasks_by_mission ON tasks(correlation_id);
CREATE TABLE IF NOT EXISTS events (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT NOT NULL,
    idx            INTEGER NOT NULL,
    kind           TEXT NOT NULL,
    payload        TEXT NOT NULL,
    prev_hash      TEXT NOT NULL,
    hash           TEXT NOT NULL,
    UNIQUE (correlation_id, idx)
);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
"""


def mission_status(tasks: list[Task], *, unmatched: bool) -> str:
    """One word for a whole mission, derived from its tasks — never stored."""
    if unmatched or not tasks:
        return "unmatched"
    states = {t.status for t in tasks}
    if S.RUNNING in states:
        return S.RUNNING.value
    done = {t.task_id for t in tasks if t.status is S.SUCCEEDED}
    ready = [t for t in tasks if t.status is S.QUEUED and set(t.dependencies) <= done]
    if ready:
        return S.QUEUED.value
    # Queued work that sits behind an unapproved task is waiting on a human too.
    for active in (S.WAITING_FOR_APPROVAL, S.QUEUED):
        if active in states:
            return active.value
    if states == {S.SUCCEEDED}:
        return "succeeded"
    for outcome in (S.FAILED, S.BLOCKED, S.CANCELLED):
        if outcome in states:
            return outcome.value
    return "unknown"  # pragma: no cover - every settled state is handled above


class TaskStore:
    """SQLite-backed task store. Safe to share between threads and processes."""

    def __init__(self, path: str | Path, *, clock: Callable[[], datetime] | None = None) -> None:
        self.path = str(path)
        self.clock = clock or (lambda: datetime.now(UTC))
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------ plumbing
    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")

    def _now(self) -> str:
        return iso(self.clock())

    def _event(self, conn: sqlite3.Connection, correlation_id: str, kind: str,
               payload: dict[str, Any]) -> None:
        last = conn.execute(
            "SELECT idx, hash FROM events WHERE correlation_id = ? ORDER BY idx DESC LIMIT 1",
            (correlation_id,),
        ).fetchone()
        index, prev = (last["idx"] + 1, last["hash"]) if last else (0, GENESIS)
        body = {**payload, "at": self._now()}
        conn.execute(
            "INSERT INTO events (correlation_id, idx, kind, payload, prev_hash, hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (correlation_id, index, kind, json.dumps(body, sort_keys=True), prev,
             _digest(index, prev, kind, body)),
        )

    def _set_status(self, conn: sqlite3.Connection, task: Task, to: TaskStatus,
                    **columns: Any) -> None:
        if to not in TRANSITIONS[task.status]:
            raise InvalidTransition(f"{task.task_id}: {task.status.value} -> {to.value}")
        columns.update(status=to.value, updated_at=self._now())
        if to in SETTLED:
            columns.setdefault("finished_at", self._now())
        assignments = ", ".join(f"{name} = ?" for name in columns)
        cursor = conn.execute(
            f"UPDATE tasks SET {assignments} WHERE task_id = ? AND status = ?",  # noqa: S608 - column names are ours
            (*columns.values(), task.task_id, task.status.value),
        )
        if cursor.rowcount != 1:
            raise InvalidTransition(f"{task.task_id}: changed underneath this update")
        self._event(conn, task.correlation_id, f"task_{to.value}",
                    {"task_id": task.task_id, "from": task.status.value,
                     **{k: v for k, v in columns.items() if k in ("error", "approved_by", "attempt")}})

    def _task(self, conn: sqlite3.Connection, task_id: str) -> Task | None:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        return Task.from_row(row) if row else None

    def _block_dependents(self, conn: sqlite3.Connection, failed: Task) -> None:
        """A failed or cancelled task can never satisfy the tasks waiting on it."""
        pending = [failed.task_id]
        while pending:
            upstream = pending.pop()
            for row in conn.execute(
                "SELECT * FROM tasks WHERE correlation_id = ? AND status IN (?, ?)",
                (failed.correlation_id, S.QUEUED.value, S.WAITING_FOR_APPROVAL.value),
            ).fetchall():
                task = Task.from_row(row)
                if upstream in task.dependencies:
                    self._set_status(conn, task, S.BLOCKED,
                                     error=f"dependency {upstream} did not succeed")
                    pending.append(task.task_id)

    # ------------------------------------------------------------------ missions
    def create_mission(
        self,
        objective: str,
        *,
        requested_by: str,
        specs: list[TaskSpec],
        plan: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> tuple[str, bool]:
        """Persist a mission and its tasks. Returns ``(correlation_id, created)``.

        A repeated ``idempotency_key`` returns the original mission instead of a
        second copy, so a client retrying a timed-out submit cannot start the
        same work twice.
        """
        ids = {s.task_id for s in specs}
        for spec in specs:
            if spec.assigned_agent == HEAD:
                raise DelegationError("the head agent cannot assign work to itself")
            if spec.depth > MAX_DEPTH or spec.depth < 1:
                raise DelegationError(
                    f"{spec.task_id}: depth {spec.depth} exceeds the delegation limit {MAX_DEPTH}")
            if spec.parent_task_id is not None and spec.parent_task_id not in ids:
                raise DelegationError(f"{spec.task_id}: parent is not in this mission")
            if spec.max_attempts < 1 or spec.timeout_seconds < 1:
                raise ValueError(f"{spec.task_id}: attempts and timeout must be positive")
        plan_waves([PlanTask(s.task_id, tuple(s.dependencies)) for s in specs])  # cycles fail closed

        correlation_id = f"msn-{uuid.uuid4().hex[:16]}"
        now = self._now()
        with self._tx() as conn:
            if idempotency_key:
                existing = conn.execute(
                    "SELECT correlation_id FROM missions WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if existing:
                    return existing["correlation_id"], False
            conn.execute(
                "INSERT INTO missions VALUES (?, ?, ?, ?, ?, ?)",
                (correlation_id, objective, requested_by, idempotency_key, now,
                 json.dumps(plan, sort_keys=True)),
            )
            self._event(conn, correlation_id, "mission_created",
                        {"objective": objective, "requested_by": requested_by,
                         "tasks": [s.task_id for s in specs]})
            for spec in specs:
                status = S.WAITING_FOR_APPROVAL if spec.gated else S.QUEUED
                budget = spec.budget_seconds or spec.own_budget
                deadline = None if spec.gated else self._deadline(budget)
                conn.execute(
                    "INSERT INTO tasks (task_id, parent_task_id, correlation_id, assigned_agent, "
                    "capability, objective, input, dependencies, status, max_attempts, "
                    "timeout_seconds, budget_seconds, deadline, risk, depth, resource, "
                    "created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (spec.task_id, spec.parent_task_id, correlation_id, spec.assigned_agent,
                     spec.capability, spec.objective, json.dumps(spec.input),
                     json.dumps(list(spec.dependencies)), status.value, spec.max_attempts,
                     spec.timeout_seconds, budget, deadline, json.dumps(spec.risk), spec.depth,
                     spec.resource, now, now),
                )
                self._event(conn, correlation_id, "task_created",
                            {"task_id": spec.task_id, "agent": spec.assigned_agent,
                             "capability": spec.capability, "status": status.value,
                             "dependencies": list(spec.dependencies)})
        return correlation_id, True

    def _deadline(self, budget_seconds: int) -> str:
        return iso(self.clock() + timedelta(seconds=budget_seconds))

    def get_mission(self, correlation_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM missions WHERE correlation_id = ?",
                               (correlation_id,)).fetchone()
            if row is None:
                return None
            tasks = [Task.from_row(r) for r in conn.execute(
                "SELECT * FROM tasks WHERE correlation_id = ? ORDER BY created_at, rowid",
                (correlation_id,)).fetchall()]
        plan = json.loads(row["plan"])
        return {
            "correlation_id": row["correlation_id"],
            "objective": row["objective"],
            "requested_by": row["requested_by"],
            "created_at": row["created_at"],
            "status": mission_status(tasks, unmatched=bool(plan.get("unmatched"))),
            "plan": plan,
            "tasks": [t.to_dict() for t in tasks],
        }

    def list_missions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT correlation_id FROM missions ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 100)),)).fetchall()
        missions = [self.get_mission(r["correlation_id"]) for r in rows]
        return [
            {k: m[k] for k in ("correlation_id", "objective", "status", "created_at")}
            | {"task_count": len(m["tasks"])}
            for m in missions if m
        ]

    def get_task(self, task_id: str) -> Task | None:
        with self._connect() as conn:
            return self._task(conn, task_id)

    # ------------------------------------------------------------------ execution
    def claim_next(
        self,
        worker_id: str,
        *,
        lease_seconds: int,
        agent_limits: dict[str, int],
        global_limit: int,
    ) -> Task | None:
        """Atomically hand the next runnable task to ``worker_id``, or ``None``.

        Runnable means: queued, past any retry backoff, every dependency
        succeeded, its agent under its concurrency limit, and no running task
        holding the same write resource (two writers never share a work tree).
        """
        moment = self.clock()
        with self._tx() as conn:
            running = [Task.from_row(r) for r in conn.execute(
                "SELECT * FROM tasks WHERE status = ?", (S.RUNNING.value,)).fetchall()]
            if len(running) >= global_limit:
                return None
            busy_agents: dict[str, int] = {}
            for t in running:
                busy_agents[t.assigned_agent] = busy_agents.get(t.assigned_agent, 0) + 1
            busy_resources = {t.resource for t in running if t.resource}

            for row in conn.execute(
                "SELECT task_id FROM tasks WHERE status = ? ORDER BY created_at, rowid",
                (S.QUEUED.value,),
            ).fetchall():
                # Re-read: failing an expired task above can block later ones in this list.
                task = self._task(conn, row["task_id"])
                if task is None or task.status is not S.QUEUED:
                    continue
                deadline = parse_iso(task.deadline)
                if deadline is not None and moment >= deadline:
                    self._set_status(conn, task, S.FAILED, error="deadline passed before the task could start")
                    self._block_dependents(conn, task)
                    continue
                not_before = parse_iso(task.not_before)
                if not_before is not None and moment < not_before:
                    continue
                if busy_agents.get(task.assigned_agent, 0) >= agent_limits.get(task.assigned_agent, 1):
                    continue
                if task.resource and task.resource in busy_resources:
                    continue
                if task.dependencies:
                    marks = ",".join("?" * len(task.dependencies))
                    done = conn.execute(
                        f"SELECT COUNT(*) FROM tasks WHERE task_id IN ({marks}) AND status = ?",  # noqa: S608
                        (*task.dependencies, S.SUCCEEDED.value),
                    ).fetchone()[0]
                    if done != len(task.dependencies):
                        continue
                self._set_status(
                    conn, task, S.RUNNING,
                    attempt=task.attempt + 1,
                    lease_owner=worker_id,
                    lease_expires_at=iso(moment + timedelta(seconds=lease_seconds)),
                    started_at=task.started_at or iso(moment),
                    not_before=None,
                )
                return self._task(conn, task.task_id)
        return None

    def renew_lease(self, task_id: str, worker_id: str, lease_seconds: int) -> tuple[bool, bool]:
        """Extend a lease. Returns ``(still_owned, cancel_requested)``."""
        with self._tx() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET lease_expires_at = ?, updated_at = ? "
                "WHERE task_id = ? AND lease_owner = ? AND status = ?",
                (iso(self.clock() + timedelta(seconds=lease_seconds)), self._now(),
                 task_id, worker_id, S.RUNNING.value),
            )
            task = self._task(conn, task_id)
        return cursor.rowcount == 1, bool(task and task.cancel_requested)

    def finish(
        self,
        task_id: str,
        worker_id: str,
        status: TaskStatus,
        *,
        output: dict[str, Any] | None = None,
        error: str | None = None,
        evidence: list[str] | None = None,
        retry_in_seconds: float | None = None,
    ) -> Task:
        """Record a running task's outcome. Only the lease holder may do this.

        ``status=QUEUED`` with ``retry_in_seconds`` is a retry; the store turns
        it into a failure if the attempt budget is already spent.
        """
        with self._tx() as conn:
            task = self._task(conn, task_id)
            if task is None or task.status is not S.RUNNING or task.lease_owner != worker_id:
                raise InvalidTransition(f"{task_id}: not running under {worker_id}")
            columns: dict[str, Any] = {
                "output": json.dumps(output) if output is not None else None,
                "error": error,
                "evidence": json.dumps(evidence or []),
                "lease_owner": None,
                "lease_expires_at": None,
            }
            if status is S.QUEUED:
                if task.attempt >= task.max_attempts:
                    status = S.FAILED
                    columns["error"] = f"{error or 'failed'} (attempt budget of {task.max_attempts} spent)"
                else:
                    columns["not_before"] = iso(self.clock() + timedelta(seconds=retry_in_seconds or 0))
            self._set_status(conn, task, status, **columns)
            if status in (S.FAILED, S.CANCELLED):
                self._block_dependents(conn, task)
            result = self._task(conn, task_id)
        assert result is not None
        return result

    def recover_expired(self) -> list[str]:
        """Re-queue (or fail) running tasks whose worker stopped renewing."""
        moment = self.clock()
        recovered: list[str] = []
        with self._tx() as conn:
            for row in conn.execute("SELECT * FROM tasks WHERE status = ?",
                                    (S.RUNNING.value,)).fetchall():
                task = Task.from_row(row)
                expires = parse_iso(task.lease_expires_at)
                if expires is None or moment < expires:
                    continue
                cleared = {"lease_owner": None, "lease_expires_at": None}
                if task.cancel_requested:
                    self._set_status(conn, task, S.CANCELLED, error="cancelled; worker lost", **cleared)
                    self._block_dependents(conn, task)
                elif task.attempt < task.max_attempts:
                    self._set_status(conn, task, S.QUEUED, error="lease expired; re-queued", **cleared)
                else:
                    self._set_status(conn, task, S.FAILED,
                                     error=f"lease expired on the last of {task.max_attempts} attempts",
                                     **cleared)
                    self._block_dependents(conn, task)
                recovered.append(task.task_id)
        return recovered

    # ------------------------------------------------------------------ control
    def cancel_mission(self, correlation_id: str, *, by: str) -> dict[str, int]:
        """Cancel everything not yet settled. Running tasks are asked to stop."""
        counts = {"cancelled": 0, "stop_requested": 0}
        with self._tx() as conn:
            if conn.execute("SELECT 1 FROM missions WHERE correlation_id = ?",
                            (correlation_id,)).fetchone() is None:
                raise KeyError(correlation_id)
            for row in conn.execute("SELECT * FROM tasks WHERE correlation_id = ?",
                                    (correlation_id,)).fetchall():
                task = Task.from_row(row)
                if task.status in (S.QUEUED, S.WAITING_FOR_APPROVAL):
                    self._set_status(conn, task, S.CANCELLED, error=f"cancelled by {by}")
                    counts["cancelled"] += 1
                elif task.status is S.RUNNING and not task.cancel_requested:
                    conn.execute("UPDATE tasks SET cancel_requested = 1, updated_at = ? "
                                 "WHERE task_id = ?", (self._now(), task.task_id))
                    counts["stop_requested"] += 1
            self._event(conn, correlation_id, "mission_cancel_requested", {"by": by, **counts})
        return counts

    def decide(self, task_id: str, *, approver: str, approve: bool, reason: str) -> Task:
        """A human decision on a gated task: approve queues it, reject cancels it."""
        with self._tx() as conn:
            task = self._task(conn, task_id)
            if task is None:
                raise KeyError(task_id)
            if task.status is not S.WAITING_FOR_APPROVAL:
                raise InvalidTransition(f"{task_id} is {task.status.value}, not waiting for approval")
            self._event(conn, task.correlation_id, "approval_decision",
                        {"task_id": task_id, "approver": approver,
                         "decision": "approved" if approve else "rejected", "reason": reason})
            if approve:
                self._set_status(conn, task, S.QUEUED, approved_by=approver,
                                 deadline=self._deadline(task.budget_seconds))
            else:
                self._set_status(conn, task, S.CANCELLED, approved_by=None,
                                 error=f"rejected by {approver}: {reason}")
                self._block_dependents(conn, task)
            result = self._task(conn, task_id)
        assert result is not None
        return result

    # ------------------------------------------------------------------ evidence
    def events(self, correlation_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT idx, kind, payload, prev_hash, hash FROM events "
                "WHERE correlation_id = ? ORDER BY idx", (correlation_id,)).fetchall()
        entries = [{"index": r["idx"], "kind": r["kind"], "payload": json.loads(r["payload"]),
                    "prev_hash": r["prev_hash"], "hash": r["hash"]} for r in rows]
        ok, bad = AuditLedger.from_entries(entries).verify()
        return {"correlation_id": correlation_id, "chain_verified": ok,
                "first_bad_index": bad, "events": entries}

    def metrics(self) -> dict[str, Any]:
        with self._connect() as conn:
            by_status = {r["status"]: r["n"] for r in conn.execute(
                "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status")}
            by_agent: dict[str, dict[str, int]] = {}
            for r in conn.execute(
                    "SELECT assigned_agent, status, COUNT(*) AS n FROM tasks GROUP BY 1, 2"):
                by_agent.setdefault(r["assigned_agent"], {})[r["status"]] = r["n"]
            retries = conn.execute(
                "SELECT COALESCE(SUM(MAX(attempt - 1, 0)), 0) FROM tasks").fetchone()[0]
            settled = conn.execute(
                "SELECT capability, started_at, finished_at FROM tasks "
                "WHERE status = ? AND started_at IS NOT NULL", (S.SUCCEEDED.value,)).fetchall()
            oldest = conn.execute("SELECT MIN(created_at) FROM tasks WHERE status = ?",
                                  (S.QUEUED.value,)).fetchone()[0]
            missions = conn.execute("SELECT COUNT(*) FROM missions").fetchone()[0]
        durations: dict[str, list[float]] = {}
        for r in settled:
            start, end = parse_iso(r["started_at"]), parse_iso(r["finished_at"])
            if start and end:
                durations.setdefault(r["capability"], []).append((end - start).total_seconds())
        oldest_at = parse_iso(oldest)
        return {
            "missions": missions,
            "tasks_by_status": by_status,
            "tasks_by_agent": by_agent,
            "queue_depth": by_status.get(S.QUEUED.value, 0),
            "awaiting_approval": by_status.get(S.WAITING_FOR_APPROVAL.value, 0),
            "oldest_queued_seconds": (round((self.clock() - oldest_at).total_seconds(), 1)
                                      if oldest_at else None),
            "retries": retries,
            "mean_duration_seconds": {k: round(sum(v) / len(v), 3) for k, v in durations.items()},
        }

    def ping(self) -> bool:
        with self._connect() as conn:
            return conn.execute("SELECT 1").fetchone()[0] == 1
