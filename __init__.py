# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass Autonomous Agent OS v8.0 — runtime.

A deterministic, stdlib-only, fail-closed orchestration layer that turns the
``agents/clearglass_agent_os`` definition into runnable code:

* :mod:`agent_os.governance`   — risk scoring + approval gating (fail-closed).
* :mod:`agent_os.roster`       — the thirteen specialist sub-agents as data.
* :mod:`agent_os.planning`     — objective -> executable DAG (waves + critical path).
* :mod:`agent_os.executive`    — expected-value strategy ranking + priority queue.
* :mod:`agent_os.intelligence` — multi-source cross-reference + contradiction detection.
* :mod:`agent_os.memory`       — ranked, persistent recall (accuracy x recency x authority).
* :mod:`agent_os.recovery`     — root-cause classification + bounded retry + escalation.
* :mod:`agent_os.learning`     — outcome capture, metrics, lessons.
* :mod:`agent_os.audit`        — append-only, tamper-evident hash-chain ledger.
* :mod:`agent_os.orchestrator` — the executive loop that produces a mission report.
* :mod:`agent_os.self_check`   — governance self-check + executive report entrypoint.

Standard library only, so it runs unchanged inside minimal CI environments,
mirroring ``clearglass-commerce`` and ``sentinel`` conventions.
"""
from __future__ import annotations

__version__ = "8.0.0"

from .audit import AuditLedger
from .executive import Strategy, rank_strategies
from .governance import RiskAssessment, RiskTier, score_action
from .intelligence import Claim, cross_reference
from .learning import LearningLog
from .memory import MemoryStore
from .orchestrator import AgentOS, MissionReport, ProposedAction
from .recovery import plan_recovery
from .state_machine import IncidentState, IncidentStateMachine, TransitionRecord
from .roster import ROSTER, SubAgent

__all__ = [
    "ROSTER",
    "AgentOS",
    "AuditLedger",
    "Claim",
    "LearningLog",
    "MemoryStore",
    "IncidentState",
    "IncidentStateMachine",
    "MissionReport",
    "ProposedAction",
    "RiskAssessment",
    "RiskTier",
    "Strategy",
    "SubAgent",
    "TransitionRecord",
    "cross_reference",
    "plan_recovery",
    "rank_strategies",
    "score_action",
    "__version__",
]
