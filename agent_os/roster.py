# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The thirteen specialist sub-agents of the Autonomous Agent OS, as data.

Kept declarative and dependency-free so the orchestrator, the self-check, and
the tests all read the roster from a single source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubAgent:
    """A specialist worker coordinated by the executive orchestration layer."""

    key: str
    name: str
    responsibilities: tuple[str, ...]
    produces: tuple[str, ...]


ROSTER: dict[str, SubAgent] = {
    a.key: a
    for a in (
        SubAgent(
            "executive",
            "Executive Agent",
            ("strategic reasoning", "priority management", "resource allocation",
             "goal decomposition", "conflict resolution", "risk acceptance",
             "mission tracking"),
            ("Mission Plan", "Priority Queue", "Execution Graph", "Risk Register",
             "Success Metrics"),
        ),
        SubAgent(
            "planning",
            "Planning Agent",
            ("dependency analysis", "critical path detection", "rollback strategy",
             "parallelization", "failure checkpoints", "cost/runtime estimation"),
            ("Execution DAG", "Critical Path", "Rollback Plan"),
        ),
        SubAgent(
            "intelligence",
            "Intelligence Agent",
            ("collect", "normalize", "validate", "cross-reference",
             "entity resolution", "contradiction detection", "confidence scoring"),
            ("Knowledge Graph Update", "Contradiction Report", "Confidence Scores"),
        ),
        SubAgent(
            "research",
            "Research Agent",
            ("academic research", "passive lawful OSINT", "government records",
             "technical/API docs", "standards", "legal references"),
            ("Evidence Pack", "Citation Graph", "Confidence Matrix"),
        ),
        SubAgent(
            "coding",
            "Coding Agent",
            ("modular architecture", "strong typing", "unit + integration tests",
             "structured logging", "secrets isolation", "security review"),
            ("Production Code", "Test Suite", "Documentation"),
        ),
        SubAgent(
            "security",
            "Security Agent",
            ("authn/authz review", "secrets + encryption", "dependency + supply chain",
             "container + network exposure", "OWASP", "MITRE ATT&CK mapping",
             "threat modeling"),
            ("Risk Score", "Patch Recommendations", "Threat Model"),
        ),
        SubAgent(
            "financial",
            "Financial Agent",
            ("revenue", "cash flow", "subscriptions", "lead generation", "pricing",
             "ROI", "CAC", "LTV"),
            ("KPI Dashboard",),
        ),
        SubAgent(
            "marketing",
            "Marketing Agent",
            ("SEO", "email", "content", "social", "ads", "landing pages",
             "analytics", "brand consistency", "A/B experiments"),
            ("Campaign Plan", "Experiment Results", "Growth Metrics"),
        ),
        SubAgent(
            "automation",
            "Automation Agent",
            ("discover repetitive tasks", "feasibility + ROI + failure-impact scoring",
             "workflow construction"),
            ("Automation Workflows",),
        ),
        SubAgent(
            "memory",
            "Memory Agent",
            ("semantic + project + decision memory", "architecture + failure history",
             "lessons learned", "accuracy/recency/authority-ranked retrieval"),
            ("Retrieved Context", "Decision History"),
        ),
        SubAgent(
            "audit",
            "Audit Agent",
            ("logic", "completeness", "security", "consistency", "performance",
             "business impact", "compliance"),
            ("Audit Score", "Improvement Report", "Regression Detection"),
        ),
        SubAgent(
            "recovery",
            "Recovery Agent",
            ("root-cause classification", "automated recovery", "escalation after "
             "all recovery paths fail"),
            ("Root Cause", "Recovery Result"),
        ),
        SubAgent(
            "learning",
            "Learning Agent",
            ("capture successes + failures + metrics", "extract lessons",
             "update knowledge graph"),
            ("Lessons Learned", "Optimization Opportunities"),
        ),
    )
}

# Failure root-cause categories the Recovery Agent classifies into.
RECOVERY_CAUSES: tuple[str, ...] = (
    "input",
    "environment",
    "dependency",
    "permissions",
    "logic",
    "external_service",
    "user_data",
)


def roster_keys() -> tuple[str, ...]:
    """Stable ordering of sub-agent keys."""
    return tuple(ROSTER.keys())
