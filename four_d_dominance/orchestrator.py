"""Orchestrator.

Ties the tiered router, memory, agents, and governance gate together into one
run loop per task: classify risk -> plan -> execute/critique (with revision) ->
decide whether the result may auto-execute or must escalate for approval. Every
step is written to an append-only audit trail, matching the repository's
"log every action" rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .agents import Critic, Executor, Planner
from .governance import GovernanceDecision, score_action
from .memory import Memory
from .models import ModelRouter


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class TaskOutcome:
    task: str
    plan_steps: int
    critic_score: int
    revisions: int
    auto_executed: bool
    governance: GovernanceDecision
    outputs: list[str]
    audit: list[dict[str, Any]]

    def summary(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "plan_steps": self.plan_steps,
            "critic_score": self.critic_score,
            "revisions": self.revisions,
            "risk_level": self.governance.level.value,
            "risk_score": self.governance.score,
            "auto_executed": self.auto_executed,
            "requires_approval": self.governance.requires_approval,
            "reason": self.governance.reason,
        }


class Orchestrator:
    """Coordinates a single task end to end."""

    def __init__(
        self,
        router: ModelRouter | None = None,
        memory: Memory | None = None,
        max_revisions: int = 1,
    ) -> None:
        self.router = router or ModelRouter()
        self.memory = memory or Memory()
        self.planner = Planner(self.router)
        self.executor = Executor(self.router)
        self.critic = Critic(self.router)
        self.max_revisions = max_revisions
        self.audit: list[dict[str, Any]] = []

    def _log(self, action: str, detail: str, decision: GovernanceDecision) -> None:
        entry = {
            "ts": _utc_now(),
            "action": action,
            "detail": detail,
            "risk_score": decision.score,
            "risk_level": decision.level.value,
        }
        self.audit.append(entry)
        self.memory.remember(entry)

    def run_task(self, task: str) -> TaskOutcome:
        decision = score_action(task)
        self._log("classify", task, decision)

        plan = self.planner.plan(task)
        outputs: list[str] = []
        best_score = 0
        total_revisions = 0

        for step in plan.steps:
            result = self.executor.execute(step)
            critique = self.critic.review(result)
            best_score = max(best_score, critique.score)

            revisions = 0
            while not critique.passed and revisions < self.max_revisions:
                result = self.executor.execute(step)
                critique = self.critic.review(result)
                best_score = max(best_score, critique.score)
                revisions += 1
            total_revisions += revisions
            outputs.append(result.output)
            self._log(f"step:{step.stage}", result.output[:80], decision)

        # Only low-risk work auto-executes. Everything else is produced as a
        # draft and held for human approval — never published by the pipeline.
        self.memory.learn(f"last_score:{task}", best_score)

        return TaskOutcome(
            task=task,
            plan_steps=len(plan.steps),
            critic_score=best_score,
            revisions=total_revisions,
            auto_executed=decision.auto_execute,
            governance=decision,
            outputs=outputs,
            audit=list(self.audit),
        )
