# Copyright (c) 2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Agent capability vocabulary and scope loader.

Every ``agents/*/agent.json`` declares a ``permissions`` list. Until now those
declarations were **documentation only** — nothing in the repo read them (see
``operations/architect-checklist/2026-W31.md``, item 3). This module is the first
half of closing that gap: one importable source of truth for what a capability
token may be, so the eventual governance wiring and the CI gate agree on the
vocabulary instead of drifting apart.

It deliberately does **not** enforce anything at runtime yet. Mapping these
tokens onto ``clearglass-commerce/control-plane/app/governance.py`` action names
— so that an undeclared or unrecognised capability inherits that module's
fail-closed "unknown action ⇒ high risk" behaviour — is a separate change that
was flagged for cross-team review before implementation. Declaring the
vocabulary is safe; silently changing what agents are allowed to do is not.

Stdlib only, per the repo convention for governance-adjacent modules.
"""
from __future__ import annotations

import json
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent

#: Canonical capability tokens. Snake_case, verb_object, coarse-grained on
#: purpose — these are risk classes to route on, not an API surface.
CANONICAL_CAPABILITIES: frozenset[str] = frozenset(
    {
        # read
        "read_repository",
        "read_public_sources",
        "read_approved_public_sources",
        "read_authorized_analytics",
        "read_kit_content",
        # analyse — read-only, no side effects
        "run_readonly_analysis",
        "run_generator_scripts",
        # draft — produces proposals, never applies them
        "draft_recommendations",
        "draft_content",
        "draft_code_changes",
        "draft_strategy",
        "draft_experiments",
        "propose_schedule",
        # orchestrate
        "route_tasks_to_subagents",
        # audit
        "write_audit_events",
        "write_redacted_audit_events",
        # RFED audit trail (agents/rfed_audit). Registered deliberately rather than
        # remapped onto the tokens above: "grounding facts" and the hash-chained
        # rfed_records ledger are specific things the generic read/audit tokens do
        # not describe, and blurring them would understate what the agent declares.
        # All five stay proposal-or-append-only — the engine gates execution, and the
        # manifest forbids updating or deleting an existing rfed_records row.
        "read_grounding_facts",
        "draft_findings",
        "propose_action",
        "write_rfed_records",
        "verify_chain",
    }
)

#: Free-text tokens already in the tree before the vocabulary existed. Accepted
#: so this change stays additive, but closed to new entries: the CI gate rejects
#: any token that is neither canonical nor listed here, which stops the drift
#: without forcing a rename sweep that nobody reviewed.
LEGACY_CAPABILITIES: frozenset[str] = frozenset(
    {
        "read authorized architecture and repository context",
        "run explicitly authorized read-only analysis and validation",
        "draft designs, code, tests, plans, and change proposals",
        "submit consequential changes for human approval",
        "write redacted append-only audit events",
    }
)

#: Every token currently accepted by the CI gate.
KNOWN_CAPABILITIES: frozenset[str] = CANONICAL_CAPABILITIES | LEGACY_CAPABILITIES

#: Capabilities that only ever produce proposals. An agent whose scope is a
#: subset of these cannot, by its own declaration, change anything outside the
#: audit log — useful for triage once the governance mapping lands.
NON_MUTATING_CAPABILITIES: frozenset[str] = frozenset(
    {
        "read_repository",
        "read_public_sources",
        "read_approved_public_sources",
        "read_authorized_analytics",
        "read_kit_content",
        "run_readonly_analysis",
        "draft_recommendations",
        "draft_content",
        "draft_code_changes",
        "draft_strategy",
        "draft_experiments",
        "propose_schedule",
        "write_audit_events",
        "write_redacted_audit_events",
        "read_grounding_facts",
        "draft_findings",
        "propose_action",
        "write_rfed_records",
        "verify_chain",
    }
)


def agent_manifest_paths() -> list[Path]:
    """Every ``agents/<name>/agent.json`` in the repo, sorted by agent name."""
    return sorted(AGENTS_DIR.glob("*/agent.json"))


def load_agent_scopes() -> dict[str, dict]:
    """Return ``{agent_name: manifest}`` for every agent that declares a scope.

    Raises ``ValueError`` on a manifest that is not valid JSON, so a malformed
    file fails loudly rather than silently dropping an agent's declared limits.
    """
    scopes: dict[str, dict] = {}
    for path in agent_manifest_paths():
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} is not valid JSON: {exc}") from exc
        scopes[path.parent.name] = manifest
    return scopes


def unknown_capabilities(permissions: list[str]) -> list[str]:
    """Tokens in ``permissions`` that are not in the accepted vocabulary."""
    return [p for p in permissions if p not in KNOWN_CAPABILITIES]


def is_non_mutating(permissions: list[str]) -> bool:
    """True when every declared capability is proposal-only."""
    return bool(permissions) and set(permissions) <= NON_MUTATING_CAPABILITIES
