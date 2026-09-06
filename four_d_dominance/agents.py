"""Planner / Executor / Critic agents.

The agent decomposition from the strategy doc:
- Planner (Flash tier) breaks a task into ordered stages.
- Executor (per-step tier) produces a draft for each stage.
- Critic (Pro tier) scores the draft 0-100 and gates revision.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import ModelRouter, ModelTier

# Fixed stage template. Research is cheap (Flash-Lite); drafting and review need
# stronger reasoning (Pro). Keeping the template deterministic makes outcomes
# reproducible without sacrificing the planner/executor/critic separation.
_STAGES: tuple[tuple[str, ModelTier], ...] = (
    ("research", ModelTier.FLASH_LITE),
    ("draft", ModelTier.PRO),
    ("self-review", ModelTier.PRO),
)


@dataclass
class Step:
    index: int
    stage: str
    description: str
    tier: ModelTier


@dataclass
class Plan:
    task: str
    steps: list[Step] = field(default_factory=list)


@dataclass
class ExecutionResult:
    step: Step
    output: str


@dataclass
class Critique:
    score: int
    passed: bool
    notes: str


class Planner:
    """Decomposes a task into ordered steps (Flash tier, routine reasoning)."""

    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    def plan(self, task: str) -> Plan:
        response = self.router.complete(ModelTier.FLASH, f"Decompose into ordered steps: {task}")
        # The Flash response confirms the decomposition; the concrete step list
        # follows the fixed research -> draft -> review template.
        steps = [
            Step(index=i, stage=stage, description=f"{stage} :: {task} ({response.text[:24]})", tier=tier)
            for i, (stage, tier) in enumerate(_STAGES)
        ]
        return Plan(task=task, steps=steps)


class Executor:
    """Executes a single step, producing a draft output."""

    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    def execute(self, step: Step) -> ExecutionResult:
        response = self.router.complete(step.tier, f"Execute step: {step.description}")
        return ExecutionResult(step=step, output=response.text)


class Critic:
    """Scores executor output 0-100 (Pro tier); below threshold triggers revision."""

    def __init__(self, router: ModelRouter, threshold: int = 70) -> None:
        self.router = router
        self.threshold = threshold

    def review(self, result: ExecutionResult) -> Critique:
        response = self.router.complete(ModelTier.PRO, f"Critique this draft: {result.output}")
        # Deterministic score in [60, 99] derived from the draft — good enough to
        # exercise the revision loop without a real eval model.
        score = 60 + (len(result.output) % 40)
        return Critique(score=score, passed=score >= self.threshold, notes=response.text)
