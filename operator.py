# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Operator — the front door to the agent OS.

Plain-language objective in, governed execution out.

The orchestrator (:mod:`agent_os.orchestrator`) can already plan, score, and
report on a mission — but it has to be *handed* tasks and proposed actions, so
until now the only thing that called it was a hardcoded demo. This module is the
missing link: it turns "audit the site and tell me what's broken" into real
capabilities, routes them through the same governance gate, executes only what
policy allows, and escalates the rest.

Design rules (these are what make it safe to run unattended):

* **The registry is real.** Every capability below maps to a command that
  actually exists and runs in this repository. There is no capability that
  pretends. If an objective matches nothing, the operator says so plainly
  instead of inventing an answer — see :attr:`OperatorResult.unmatched`.
* **Governance decides, not the operator.** Each matched capability becomes a
  ``ProposedAction`` scored by :func:`agent_os.governance.score_action`. Only
  actions the mission report lists as auto-executable may run. Unknown actions
  score 85 (HIGH) and are gated — fail-closed by construction.
* **Read-only by default.** Capabilities that modify the repo are marked
  ``writes=True``, are scored as ``publish_content`` (MEDIUM → gated), and are
  additionally refused unless the caller passes ``allow_writes=True``. Two
  independent locks, because one is not enough for unattended execution.
* **Nothing executes unless asked.** ``handle()`` plans and reports; it only
  shells out when ``execute=True``.
* **Everything is audited.** The mission ledger is hash-chained and verified.

Stdlib only, so it runs in the same minimal CI environments as the rest of the
governed stack.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

from .audit import AuditLedger
from .orchestrator import AgentOS, ProposedAction

# A runner takes an argv and returns (exit_code, combined_output).
Runner = Callable[[Sequence[str], Path], "tuple[int, str]"]

_REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Capability:
    """One thing the operator can actually do.

    ``command`` is executed verbatim; ``action`` is the governance action name
    that decides whether it may auto-execute.
    """

    key: str
    title: str
    intents: tuple[str, ...]          # phrases that route an objective here
    action: str                       # governance action name (scored)
    command: tuple[str, ...]          # argv — must really exist
    writes: bool = False              # does it modify the working tree?
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key, "title": self.title, "action": self.action,
            "command": " ".join(self.command), "writes": self.writes,
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# The registry. Every entry here was verified to exist and run in this repo.
# Read-only capabilities use `run_audit` (LOW -> auto). Anything that writes
# uses `publish_content` (MEDIUM -> gated) so a human approves the diff.
# ---------------------------------------------------------------------------
CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        "site.audit", "Site audit (PERCIVAL scan)",
        ("audit", "scan", "check the site", "site health", "seo", "what's broken",
         "whats broken", "accessibility", "a11y", "review the site"),
        "run_audit",
        (sys.executable, "-c",
         "import sys; sys.path.insert(0,'sentinel'); "
         "from sentinel.percival import Percival; "
         "print(Percival('.').scan().brief())"),
        description="SEO / accessibility / brand / link audit of every page.",
    ),
    Capability(
        "links.check", "Internal link freshness",
        ("links", "link check", "broken link", "internal links", "linking"),
        "run_audit",
        (sys.executable, "tools/internal_links.py", "--check"),
        description="Verify every generated 'Continue exploring' block is fresh.",
    ),
    Capability(
        "workflows.audit", "Workflow doctor",
        ("workflow", "workflows", "ci", "actions", "pipeline", "yaml"),
        "run_audit",
        (sys.executable, "scripts/workflow_doctor.py"),
        description="Audit GitHub Actions workflows for drift and breakage.",
    ),
    Capability(
        "commerce.selfcheck", "Commerce governance self-check",
        ("commerce", "store", "shop", "orders", "governance", "payouts"),
        "run_audit",
        (sys.executable, "-m", "app.daily_loop", "--json"),
        description="Commerce control-plane governance self-check + report.",
    ),
    Capability(
        "agentos.selfcheck", "Agent OS self-check",
        ("agent os", "agentos", "self-check", "self check", "orchestrator",
         "governance gate"),
        "run_audit",
        (sys.executable, "-m", "agent_os"),
        description="Verify the governance gate and audit chain still hold.",
    ),
    Capability(
        "store.smoke", "Storefront smoke test",
        ("storefront", "smoke", "checkout", "catalog"),
        "run_audit",
        (sys.executable, "-m", "bots.store_smoke_bot"),
        description="Catalog + checkout-health smoke check.",
    ),
    # --- writes: gated, and refused without allow_writes ---
    Capability(
        "links.refresh", "Regenerate internal links",
        ("regenerate links", "refresh links", "fix links", "rebuild links"),
        "publish_content",
        (sys.executable, "tools/internal_links.py"),
        writes=True,
        description="Regenerate the pillar/cluster internal-link blocks.",
    ),
)

_COMMERCE_CWD = "clearglass-commerce/control-plane"


def _default_runner(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
    """Execute a capability. Captures output; never raises on non-zero exit."""
    try:
        proc = subprocess.run(
            list(argv), cwd=str(cwd), capture_output=True, text=True, timeout=600,
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out after 600s"
    except OSError as exc:  # command missing / not executable
        return 127, f"could not execute: {exc}"


@dataclass
class Execution:
    """The real result of running one capability."""

    key: str
    command: str
    exit_code: int
    ok: bool
    output: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class OperatorResult:
    objective: str
    matched: list[str] = field(default_factory=list)
    unmatched: bool = False
    executed: list[Execution] = field(default_factory=list)
    escalated: list[dict[str, object]] = field(default_factory=list)
    refused: list[dict[str, object]] = field(default_factory=list)
    mission: dict[str, object] = field(default_factory=dict)
    audit_verified: bool = False
    summary: str = ""

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["executed"] = [e.to_dict() for e in self.executed]
        return d


class Operator:
    """Routes a plain-language objective to governed, real execution."""

    def __init__(
        self,
        root: Optional[Path | str] = None,
        *,
        capabilities: Sequence[Capability] = CAPABILITIES,
        runner: Optional[Runner] = None,
    ) -> None:
        self.root = Path(root) if root is not None else _REPO_ROOT
        self.capabilities = tuple(capabilities)
        self.runner = runner or _default_runner

    # ------------------------------------------------------------------ #
    # routing
    # ------------------------------------------------------------------ #
    def match(self, objective: str) -> list[Capability]:
        """Capabilities whose intents appear in the objective, best first.

        Deliberately conservative: no fuzzy guessing. If the objective doesn't
        name something the system can actually do, it matches nothing and the
        operator reports that honestly rather than picking a plausible action.
        """
        text = " ".join(objective.lower().split())
        scored: list[tuple[int, int, Capability]] = []
        for i, cap in enumerate(self.capabilities):
            hits = sum(1 for kw in cap.intents if kw in text)
            if hits:
                # longest matching intent wins ties — more specific phrasing.
                specificity = max((len(kw) for kw in cap.intents if kw in text), default=0)
                scored.append((hits * 100 + specificity, -i, cap))
        scored.sort(key=lambda t: (-t[0], -t[1]))
        return [c for _, _, c in scored]

    def _cwd_for(self, cap: Capability) -> Path:
        return self.root / _COMMERCE_CWD if cap.key == "commerce.selfcheck" else self.root

    # ------------------------------------------------------------------ #
    # the front door
    # ------------------------------------------------------------------ #
    def handle(
        self,
        objective: str,
        *,
        execute: bool = False,
        allow_writes: bool = False,
        ledger: Optional[AuditLedger] = None,
    ) -> OperatorResult:
        """Plan (and optionally run) an objective under governance."""
        ledger = ledger if ledger is not None else AuditLedger()
        result = OperatorResult(objective=objective)
        matched = self.match(objective)

        if not matched:
            result.unmatched = True
            result.summary = (
                "No registered capability matches this objective. The operator "
                "will not improvise an action. Registered capabilities: "
                + ", ".join(c.key for c in self.capabilities)
            )
            ledger.append("objective_unmatched", {"objective": objective})
            result.audit_verified = ledger.verify()[0]
            return result

        return self._run_plan(objective, matched, result, ledger,
                              execute=execute, allow_writes=allow_writes)

    def sweep(
        self,
        *,
        execute: bool = True,
        ledger: Optional[AuditLedger] = None,
    ) -> OperatorResult:
        """Run every read-only capability — the unattended daily pass.

        Deliberately excludes anything that writes, so this is safe to run on a
        schedule with no human present. Governance still scores each action.
        """
        objective = "Scheduled read-only sweep of all registered capabilities"
        caps = [c for c in self.capabilities if not c.writes]
        result = OperatorResult(objective=objective, matched=[c.key for c in caps])
        return self._run_plan(
            objective, caps, result,
            ledger if ledger is not None else AuditLedger(),
            execute=execute, allow_writes=False,
        )

    def _run_plan(
        self,
        objective: str,
        matched: list[Capability],
        result: OperatorResult,
        ledger: AuditLedger,
        *,
        execute: bool,
        allow_writes: bool,
    ) -> OperatorResult:
        result.matched = [c.key for c in matched]

        # Governance decides which may auto-execute.
        actions = [
            ProposedAction(
                action=c.action,
                summary=f"{c.key}: {c.title}",
                payload={"capability": c.key, "writes": c.writes},
                confidence=0.9,
                evidence=(f"registered capability {c.key} -> {' '.join(c.command)}",),
            )
            for c in matched
        ]
        report = AgentOS().run_mission(
            objective, proposed_actions=actions, ledger=ledger,
            assumptions=[f"Capability registry resolved {len(matched)} capability(ies)."],
        )
        result.mission = report.to_dict()
        auto = set(report.validation_results.get("auto_actions", []))  # type: ignore[union-attr]

        for cap in matched:
            if cap.action not in auto:
                result.escalated.append(
                    {"key": cap.key, "action": cap.action,
                     "reason": "governance requires human approval"})
                continue
            if cap.writes and not allow_writes:
                result.refused.append(
                    {"key": cap.key, "action": cap.action,
                     "reason": "modifies the working tree; re-run with allow_writes"})
                continue
            if not execute:
                continue
            code, out = self.runner(cap.command, self._cwd_for(cap))
            ledger.append("capability_executed",
                          {"capability": cap.key, "exit_code": code})
            result.executed.append(
                Execution(cap.key, " ".join(cap.command), code, code == 0, out))

        result.audit_verified = ledger.verify()[0]
        result.summary = self._summarize(result, execute)
        return result

    @staticmethod
    def _summarize(r: OperatorResult, execute: bool) -> str:
        bits: list[str] = []
        if r.executed:
            ok = sum(1 for e in r.executed if e.ok)
            bits.append(f"{ok}/{len(r.executed)} capability(ies) ran clean")
        elif not execute:
            runnable = len(r.matched) - len(r.escalated) - len(r.refused)
            bits.append(f"planned only ({runnable} auto-executable) — pass execute=True to run")
        if r.escalated:
            bits.append(f"{len(r.escalated)} escalated for approval")
        if r.refused:
            bits.append(f"{len(r.refused)} refused (writes not allowed)")
        return "; ".join(bits) or "nothing to do"


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m agent_os.operator",
        description="Ask the agent OS to do something. Governed; read-only by default.",
    )
    ap.add_argument("objective", nargs="*", help="what you want done, in plain language")
    ap.add_argument("--execute", action="store_true", help="actually run auto-approved capabilities")
    ap.add_argument("--allow-writes", action="store_true", help="permit capabilities that modify the repo")
    ap.add_argument("--list", action="store_true", help="list registered capabilities and exit")
    ap.add_argument("--sweep", action="store_true",
                    help="run every read-only capability (the unattended daily pass)")
    ns = ap.parse_args(argv)

    if ns.sweep:
        res = Operator().sweep(execute=True)
        print(json.dumps(res.to_dict(), indent=2))
        return 1 if any(not e.ok for e in res.executed) else 0

    if ns.list or not ns.objective:
        print(json.dumps({"capabilities": [c.to_dict() for c in CAPABILITIES]}, indent=2))
        return 0

    res = Operator().handle(
        " ".join(ns.objective), execute=ns.execute, allow_writes=ns.allow_writes)
    print(json.dumps(res.to_dict(), indent=2))
    # Unmatched or a failed execution is a non-zero exit so CI can gate on it.
    if res.unmatched or any(not e.ok for e in res.executed):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
