# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The worker agents the head agent may delegate to, as a checked registry.

Each agent is a contract: what it is for, which capabilities it may run, which
tools (scripts or modules) those capabilities are allowed to invoke, what it
may read or write, its input and output schema, and its time, retry and
concurrency limits. :func:`validate_registry` cross-checks all of it; the head
agent refuses to start on a registry that does not validate.

Capabilities are the operator's verified registry (:mod:`agent_os.operator`)
plus the six below. Every command exists in this repository — the operator's
"no capability that pretends" rule carries over.

There is deliberately no capability that deploys, pushes, sends a message or
moves money. Those stay with humans (``ALWAYS_ESCALATE``); the deployment agent
reports readiness and nothing more.
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import freshness, readiness
from .operator import CAPABILITIES as OPERATOR_CAPABILITIES
from .operator import Capability

EXTRA_CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        "security.secrets", "Secret scan",
        ("secret", "credential", "leak", "security"),
        "run_audit",
        (sys.executable, "scripts/secret_scan.py", "--json"),
        description="Scan the working tree for committed credentials (exit 1 = findings).",
    ),
    Capability(
        "security.workflows", "Workflow security audit",
        ("security", "supply chain", "pinning", "pinned", "permissions audit"),
        "run_audit",
        (sys.executable, "scripts/audit_github_actions.py", "--json"),
        description="Permissions, SHA pinning and trigger safety of every workflow.",
    ),
    Capability(
        "data.freshness", "Live-data freshness",
        ("freshness", "live data", "data feed", "feed status", "dataset", "data source", "stale data"),
        "read_metrics",
        (sys.executable, "-m", "agent_os.freshness"),
        description="Per-source state of the published feeds from their recorded provenance.",
    ),
    Capability(
        "data.ieso.refresh", "Refresh the IESO grid feed",
        ("refresh grid", "refresh ieso", "ieso", "grid data", "power grid"),
        "publish_content",
        (sys.executable, "scripts/ieso_public_feed.py", "--strict"),
        writes=True,
        description="Fetch IESO public reports into data/grid/ieso-public.json.",
    ),
    Capability(
        "data.minerals.refresh", "Refresh the critical-minerals feed",
        ("refresh minerals", "minerals data", "minerals feed", "critical minerals"),
        "publish_content",
        (sys.executable, "scripts/minerals_data_sync.py"),
        writes=True,
        description="Fetch Government of Canada news into feeds/minerals/.",
    ),
    Capability(
        "deploy.readiness", "Deployment readiness",
        ("deploy", "release", "readiness", "ready to ship"),
        "read_metrics",
        (sys.executable, "-m", "agent_os.readiness"),
        description="Which commit would ship and whether the tree is clean. Never deploys.",
    ),
)

HEAD_CAPABILITIES: tuple[Capability, ...] = OPERATOR_CAPABILITIES + EXTRA_CAPABILITIES

#: Every task carries exactly this input; nothing a caller types reaches argv.
TASK_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"capability": {"type": "string"}},
    "required": ["capability"],
    "additionalProperties": False,
}

#: What a worker returns. ``json`` is present when the capability emits JSON.
TASK_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "exit_code": {"type": "integer"},
        "stdout": {"type": "string"},
        "stderr": {"type": "string"},
        "json": {},
        "duration_ms": {"type": "integer"},
        "truncated": {"type": "boolean"},
    },
    "required": ["exit_code", "stdout", "stderr", "duration_ms"],
}


@dataclass(frozen=True)
class AgentSpec:
    key: str
    name: str
    purpose: str
    capabilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    data_access: str
    timeout_seconds: int
    max_attempts: int
    max_concurrency: int
    completion: str
    on_failure: str
    may_write: bool = False

    def to_dict(self) -> dict[str, Any]:
        row = dict(self.__dict__)
        row["input_schema"] = TASK_INPUT_SCHEMA
        row["output_schema"] = TASK_OUTPUT_SCHEMA
        return row


AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        "repository", "Repository & implementation agent",
        "Regenerates generated repository assets after a reviewed change.",
        ("links.refresh",),
        ("script:tools/internal_links.py",),
        "reads and writes the working tree; never commits or pushes",
        timeout_seconds=300, max_attempts=2, max_concurrency=1,
        completion="generator exits 0; the diff is left for human review",
        on_failure="fail the task; dependents are blocked; nothing is committed",
        may_write=True,
    ),
    AgentSpec(
        "verification", "Test & verification agent",
        "Runs the repository's own audits and self-checks and reports their result.",
        ("site.audit", "links.check", "workflows.audit", "agentos.selfcheck",
         "commerce.selfcheck", "store.smoke"),
        ("inline:site.audit", "script:tools/internal_links.py", "script:scripts/workflow_doctor.py",
         "module:agent_os", "module:app.daily_loop", "module:bots.store_smoke_bot"),
        "read-only: working tree and committed data",
        timeout_seconds=600, max_attempts=2, max_concurrency=2,
        completion="the check exits 0",
        on_failure="a non-zero exit is a finding, not a flake: fail without retry; "
                   "only a timeout is retried",
    ),
    AgentSpec(
        "integration", "API & live-data integration agent",
        "Refreshes the published live-data feeds and reports their freshness.",
        ("data.freshness", "data.ieso.refresh", "data.minerals.refresh"),
        ("module:agent_os.freshness", "script:scripts/ieso_public_feed.py",
         "script:scripts/minerals_data_sync.py"),
        "network: reports-public.ieso.ca and api.io.canada.ca (read-only GET); "
        "writes data/grid/ and feeds/minerals/ only via the gated refreshes",
        timeout_seconds=180, max_attempts=2, max_concurrency=1,
        completion="freshness report validates; a refresh exits 0 with every source fetched",
        on_failure="the fetchers keep the last good snapshot and record the error; "
                   "the task fails and the freshness report shows the source as stale or never retrieved",
        may_write=True,
    ),
    AgentSpec(
        "security", "Security review agent",
        "Scans for committed credentials and audits workflow permissions and pinning.",
        ("security.secrets", "security.workflows"),
        ("script:scripts/secret_scan.py", "script:scripts/audit_github_actions.py"),
        "read-only: working tree",
        timeout_seconds=300, max_attempts=2, max_concurrency=1,
        completion="scanner exits 0 and emits valid JSON",
        on_failure="findings fail the task and block a readiness report in the same mission",
    ),
    AgentSpec(
        "deployment", "Deployment & operations agent",
        "Reports which commit would ship and whether the tree is clean. Never deploys.",
        ("deploy.readiness",),
        ("module:agent_os.readiness",),
        "read-only: git metadata",
        timeout_seconds=60, max_attempts=1, max_concurrency=1,
        completion="readiness report validates and the tree is clean",
        on_failure="report not-ready; production deployment stays manual and approval-gated",
    ),
)


def tool_of(cap: Capability) -> str:
    """The tool a capability invokes: ``script:<path>``, ``module:<name>`` or ``inline:<key>``."""
    argv = list(cap.command)
    if argv and argv[0] == sys.executable:
        argv = argv[1:]
    if not argv:
        return f"invalid:{cap.key}"
    if argv[0] == "-m" and len(argv) > 1:
        return f"module:{argv[1]}"
    if argv[0] == "-c":
        return f"inline:{cap.key}"
    return f"script:{argv[0]}"


def _secret_scan(document: Any) -> list[str]:
    if not isinstance(document, dict) or not isinstance(document.get("findings"), list):
        return ["secret scan did not report findings"]
    return []


def _workflow_audit(document: Any) -> list[str]:
    if not isinstance(document, list) or not all(isinstance(r, dict) and "status" in r for r in document):
        return ["workflow audit did not report a status per workflow"]
    return []


def _workflow_summary(document: Any) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    for row in document:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    return {
        "workflows": len(document),
        "by_status": by_status,
        "errors": {r["workflow"]: r["errors"] for r in document if r.get("errors")},
    }


#: Compact forms for reports too large to store whole (the full stdout hash
#: stays in the evidence, so the summary can be checked against a re-run).
SUMMARIZERS: dict[str, Callable[[Any], Any]] = {
    "security.workflows": _workflow_summary,
}

#: Capabilities whose stdout must be JSON, and the check that accepts it.
VALIDATORS: dict[str, Callable[[Any], list[str]]] = {
    "security.secrets": _secret_scan,
    "security.workflows": _workflow_audit,
    "data.freshness": freshness.validate,
    "deploy.readiness": readiness.validate,
}


def validate_registry(agents: tuple[AgentSpec, ...] = AGENTS,
                      capabilities: tuple[Capability, ...] = HEAD_CAPABILITIES) -> list[str]:
    """Every way the registry could let an agent run something it should not."""
    problems: list[str] = []
    by_key = {c.key: c for c in capabilities}
    owners: dict[str, str] = {}
    for agent in agents:
        if agent.key == "head":
            problems.append("no worker may be called 'head'")
        if agent.max_attempts < 1 or agent.timeout_seconds < 1 or agent.max_concurrency < 1:
            problems.append(f"{agent.key}: limits must be positive")
        for key in agent.capabilities:
            cap = by_key.get(key)
            if cap is None:
                problems.append(f"{agent.key}: unknown capability {key}")
                continue
            if key in owners:
                problems.append(f"{key}: assigned to both {owners[key]} and {agent.key}")
            owners[key] = agent.key
            if tool_of(cap) not in agent.allowed_tools:
                problems.append(f"{agent.key}: {key} invokes {tool_of(cap)}, which it is not allowed")
            if cap.writes and not agent.may_write:
                problems.append(f"{agent.key}: {key} writes but the agent is read-only")
    for key in by_key:
        if key not in owners:
            problems.append(f"{key}: no agent owns this capability")
    return problems
