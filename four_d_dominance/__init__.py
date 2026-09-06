"""4-D Dominance Activation system.

A stdlib-only implementation of the orchestrator-first, multi-agent framework
described in ``4D_DOMINANCE_ACTIVATION.md``. It coordinates work across four
domains (Web, AI, Corporate, Brand) using a Planner / Executor / Critic
decomposition on top of a tiered model router, a short/long-term memory layer,
and a governance gate that mirrors the repository safety model
(read-only analysis -> draft -> human approval -> execution).

The default model backend is a deterministic offline mock, so the whole
pipeline runs with no API keys (the same "mock mode" philosophy as the
commerce control plane). Swap in a real backend by passing a callable to
``ModelRouter``.
"""
from __future__ import annotations

from .agents import Critic, Critique, ExecutionResult, Executor, Plan, Planner, Step
from .governance import GovernanceDecision, RiskLevel, score_action
from .memory import Memory
from .models import ModelResponse, ModelRouter, ModelTier
from .orchestrator import Orchestrator, TaskOutcome

__all__ = [
    "Critic",
    "Critique",
    "ExecutionResult",
    "Executor",
    "GovernanceDecision",
    "Memory",
    "ModelResponse",
    "ModelRouter",
    "ModelTier",
    "Orchestrator",
    "Plan",
    "Planner",
    "RiskLevel",
    "Step",
    "TaskOutcome",
    "score_action",
]

__version__ = "1.0.0"
