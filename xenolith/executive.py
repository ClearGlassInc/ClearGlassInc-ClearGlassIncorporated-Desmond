# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH executive layer — objectives into policy-constrained missions.

The strategic nucleus. It does not perform work; it decides what work is worth
doing, in what order, and whether the lattice is currently in a state to do it.

* An **objective** is what the operator wants, with a value and a deadline.
* A **mission** is an objective decomposed into tasks, each bound to a domain
  and an action class the policy engine already knows about. A mission
  referencing an unknown action fails at planning time, not at execution time.
* **Priority** is computed, not declared: value, urgency against the deadline,
  risk drag, and the health of the domain that would have to execute it. A task
  nobody healthy can run sinks, which is what stops the lattice from queueing
  work into a hole.

Missions commit through the policy gate like anything else, so committing a
plan is itself an approvable act.

Stdlib only.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Sequence

from .constants import Domain, LatticeError, RiskTier


#: Wall-clock window against which absolute deadline pressure is measured.
#: A deadline further out than this contributes no absolute urgency of its own.
REFERENCE_HORIZON_SECONDS = 86_400.0


class ExecutiveError(LatticeError):
    """A malformed objective, mission, or unknown task action."""


class MissionState(str, Enum):
    DRAFT = "draft"
    COMMITTED = "committed"
    EXECUTING = "executing"
    COMPLETE = "complete"
    ABORTED = "aborted"
    BLOCKED = "blocked"


@dataclass
class Objective:
    """What the operator wants, and how much it is worth."""

    objective_id: str
    statement: str
    value: int
    deadline: float | None = None
    owner: str = "operator"
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ExecutiveError("objective statement is required")
        if not 0 <= self.value <= 100:
            raise ExecutiveError("objective value must be between 0 and 100")

    def urgency(self, now: float | None = None) -> float:
        """0.0–1.0. No deadline means baseline urgency, never maximum.

        Two pressures, whichever is greater:

        * **Absolute** — how close the deadline is in wall-clock terms. Work due
          in ten minutes is urgent the moment it is declared; measuring only the
          consumed fraction of its window would rank it at zero.
        * **Proportional** — how much of the allotted window has been spent. This
          is what makes a long-running objective climb as its deadline nears.

        An objective without a deadline sits at a baseline so it neither starves
        genuinely time-boxed work nor gets starved by it.
        """
        if self.deadline is None:
            return 0.35
        now = time.time() if now is None else now
        remaining = self.deadline - now
        if remaining <= 0:
            return 1.0
        absolute = 1.0 - min(1.0, remaining / REFERENCE_HORIZON_SECONDS)
        horizon = max(1.0, self.deadline - self.created_at)
        consumed = 1.0 - remaining / horizon
        return round(max(0.0, min(1.0, max(absolute, consumed))), 4)

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "statement": self.statement,
            "value": self.value,
            "deadline": self.deadline,
            "owner": self.owner,
            "urgency": self.urgency(),
            "created_at": self.created_at,
        }


@dataclass
class Task:
    """One executable step, bound to a domain and a known action class."""

    task_id: str
    action: str
    domain: Domain
    summary: str
    assigned_to: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    targets: tuple[str, ...] = ()
    state: str = "planned"
    risk_score: int = 0
    tier: RiskTier = RiskTier.LOW
    priority: float = 0.0
    blocked_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "action": self.action,
            "domain": self.domain.value,
            "summary": self.summary,
            "assigned_to": self.assigned_to,
            "targets": list(self.targets),
            "state": self.state,
            "risk_score": self.risk_score,
            "tier": self.tier.value,
            "priority": round(self.priority, 4),
            "blocked_reason": self.blocked_reason,
        }


@dataclass
class Mission:
    """An objective decomposed into ordered, governed work."""

    mission_id: str
    objective: Objective
    tasks: list[Task] = field(default_factory=list)
    state: MissionState = MissionState.DRAFT
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    committed_by: str | None = None
    created_at: float = field(default_factory=time.time)

    @property
    def blocked(self) -> tuple[Task, ...]:
        return tuple(t for t in self.tasks if t.state == "blocked")

    @property
    def executable(self) -> tuple[Task, ...]:
        return tuple(t for t in self.tasks if t.state in ("planned", "ready"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "objective": self.objective.as_dict(),
            "state": self.state.value,
            "trace_id": self.trace_id,
            "committed_by": self.committed_by,
            "created_at": self.created_at,
            "tasks": [t.as_dict() for t in sorted(self.tasks, key=lambda t: -t.priority)],
        }


@dataclass(frozen=True)
class TaskSpec:
    """Planner input: what a task should do, before risk is known."""

    action: str
    domain: Domain | str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    targets: tuple[str, ...] = ()
    assigned_to: str | None = None


class ExecutiveCore:
    """Plans, prioritizes and reports on missions."""

    def __init__(self, policy: Any, registry: Any | None = None) -> None:
        self._policy = policy
        self._registry = registry
        self._objectives: dict[str, Objective] = {}
        self._missions: dict[str, Mission] = {}
        self._counter = 0

    # ------------------------------------------------------------------ #
    # Objectives
    # ------------------------------------------------------------------ #
    def declare(
        self,
        statement: str,
        value: int,
        deadline: float | None = None,
        owner: str = "operator",
    ) -> Objective:
        self._counter += 1
        objective = Objective(
            objective_id=f"obj-{self._counter:04d}",
            statement=statement,
            value=value,
            deadline=deadline,
            owner=owner,
        )
        self._objectives[objective.objective_id] = objective
        return objective

    def objectives(self) -> tuple[Objective, ...]:
        return tuple(sorted(self._objectives.values(), key=lambda o: o.objective_id))

    # ------------------------------------------------------------------ #
    # Planning
    # ------------------------------------------------------------------ #
    def plan(self, objective: Objective, specs: Sequence[TaskSpec]) -> Mission:
        """Decompose an objective into a risk-scored, prioritized mission.

        Every task's action must already exist in the policy rule set. A plan
        built on an unknown capability is rejected here rather than discovered
        halfway through execution.
        """
        if not specs:
            raise ExecutiveError("a mission needs at least one task")

        mission = Mission(mission_id=f"msn-{len(self._missions) + 1:04d}", objective=objective)
        for index, spec in enumerate(specs, start=1):
            rule = self._policy.rule(spec.action)
            if rule is None:
                raise ExecutiveError(
                    f"task {index} references unknown action '{spec.action}' — "
                    "add a policy rule before planning against it"
                )
            domain = Domain(spec.domain)
            task = Task(
                task_id=f"{mission.mission_id}-t{index:02d}",
                action=spec.action,
                domain=domain,
                summary=spec.summary,
                assigned_to=spec.assigned_to,
                payload=dict(spec.payload),
                targets=tuple(spec.targets),
            )
            task.risk_score = rule.base_risk
            task.tier = RiskTier.from_score(task.risk_score)
            task.priority = self._priority(objective, task)
            mission.tasks.append(task)

        mission.tasks.sort(key=lambda t: -t.priority)
        self._missions[mission.mission_id] = mission
        return mission

    def _priority(self, objective: Objective, task: Task) -> float:
        """Blend value, urgency, risk drag and executor health into one number."""
        value = objective.value / 100.0
        urgency = objective.urgency()

        # Risk is drag, not a veto: a high-risk task can still be top of the
        # queue if it is valuable and urgent — it just won't auto-execute.
        risk_drag = 1.0 - (task.risk_score / 100.0) * 0.5

        health = 1.0
        if self._registry is not None:
            if task.assigned_to:
                record = self._registry.find(task.assigned_to)
                health = record.health if record and record.status.can_act else 0.15
            else:
                peers = [a for a in self._registry.by_domain(task.domain) if a.status.can_act]
                health = (sum(a.health for a in peers) / len(peers)) if peers else 0.2

        return round((0.4 * value + 0.35 * urgency + 0.25 * risk_drag) * (0.5 + 0.5 * health), 4)

    # ------------------------------------------------------------------ #
    # Commitment
    # ------------------------------------------------------------------ #
    def commit(self, mission: Mission, committed_by: str) -> Mission:
        """Move a mission from DRAFT to COMMITTED under a named commander."""
        if mission.state is not MissionState.DRAFT:
            raise ExecutiveError(f"mission {mission.mission_id} is already {mission.state.value}")
        if not committed_by.strip():
            raise ExecutiveError("commit requires a named commander")
        mission.state = MissionState.COMMITTED
        mission.committed_by = committed_by.strip()
        return mission

    def block(self, mission: Mission, task_id: str, reason: str) -> Task:
        """Mark a task blocked — typically because policy gated it."""
        task = next((t for t in mission.tasks if t.task_id == task_id), None)
        if task is None:
            raise ExecutiveError(f"unknown task: {task_id}")
        task.state = "blocked"
        task.blocked_reason = reason
        if all(t.state == "blocked" for t in mission.tasks):
            mission.state = MissionState.BLOCKED
        return task

    def complete(self, mission: Mission, task_id: str) -> Task:
        task = next((t for t in mission.tasks if t.task_id == task_id), None)
        if task is None:
            raise ExecutiveError(f"unknown task: {task_id}")
        task.state = "complete"
        if all(t.state in ("complete", "blocked") for t in mission.tasks):
            mission.state = (
                MissionState.COMPLETE
                if all(t.state == "complete" for t in mission.tasks)
                else MissionState.BLOCKED
            )
        else:
            mission.state = MissionState.EXECUTING
        return task

    def missions(self, state: MissionState | None = None) -> tuple[Mission, ...]:
        items = sorted(self._missions.values(), key=lambda m: m.mission_id)
        return tuple(m for m in items if state is None or m.state is state)

    def mission(self, mission_id: str) -> Mission:
        try:
            return self._missions[mission_id]
        except KeyError:
            raise ExecutiveError(f"unknown mission: {mission_id}") from None

    # ------------------------------------------------------------------ #
    # Executive reporting
    # ------------------------------------------------------------------ #
    def brief(self, extra: Iterable[str] = ()) -> dict[str, Any]:
        """The executive summary: posture, queue, blockers, next actions."""
        missions = self.missions()
        tasks = [t for m in missions for t in m.tasks]
        blocked = [t for t in tasks if t.state == "blocked"]
        high_risk = [t for t in tasks if t.tier.blocks_until_approved]
        ranked = sorted(tasks, key=lambda t: -t.priority)[:5]

        posture = "nominal"
        if blocked and len(blocked) >= max(1, len(tasks) // 2):
            posture = "impeded"
        elif high_risk:
            posture = "awaiting-authority"

        return {
            "posture": posture,
            "objectives": len(self._objectives),
            "missions": len(missions),
            "missions_by_state": {
                state.value: sum(1 for m in missions if m.state is state) for state in MissionState
            },
            "tasks": len(tasks),
            "tasks_blocked": len(blocked),
            "tasks_requiring_authority": len(high_risk),
            "next_actions": [
                {
                    "task_id": t.task_id,
                    "action": t.action,
                    "domain": t.domain.value,
                    "priority": round(t.priority, 4),
                    "tier": t.tier.value,
                    "summary": t.summary,
                }
                for t in ranked
            ],
            "notes": list(extra),
        }
