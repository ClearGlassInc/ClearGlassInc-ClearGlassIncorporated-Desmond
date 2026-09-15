#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Governance for the repository's own automation — what a bot may merge, and when.

The commerce control plane gates actions that move a customer's money
(``control-plane/app/governance.py``). This module gates actions that change the
system that moves it. The failure it exists to prevent is the one where an agent
with repository write access "fixes" its way through a payment path at 3am, every
check it broke reports green because Actions is not dispatching runners, and the
first symptom is a customer being charged the wrong amount.

Two independent questions, both of which must answer yes before anything merges
without a human:

1. **Is this change small enough?** :func:`classify_change` scores the *paths* a
   change touches. Anything reaching payments, auth, workflows, migrations,
   infrastructure, dependencies or customer-facing legal text is HIGH and is never
   auto-merged, however small the diff looks.
2. **Is the system healthy enough to be changing itself right now?**
   :func:`evaluate_breakers` answers from observed state — deploy history, scan
   results, how much the bot has already merged today. A repository in the middle
   of a failed deploy or a red secret scan is one where the *next* automated change
   is most likely to compound the problem, so mutation stops entirely.

Stdlib only, no network, no repository writes, and fail-closed throughout: an
unrecognised path is MEDIUM (needs a human), and missing state is treated as the
unsafe value rather than the convenient one. Callers are workflows, so the CLI's
exit code is the contract — non-zero means do not proceed.

    python3 scripts/automation_governance.py --self-check
    python3 scripts/automation_governance.py --paths docs/X.md README.md
    python3 scripts/automation_governance.py --state state.json
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

#: Bump when the tables or gating logic below change, so an audit record says
#: which policy produced it. Mirrors RFED's POLICY_VERSION convention.
POLICY_VERSION = "1.0.0"


class ChangeRisk(str, Enum):
    """What a change is allowed to do on its own."""

    LOW = "low"        # auto-merge permitted once every required check passes
    MEDIUM = "medium"  # pull request + human approval
    HIGH = "high"      # pull request + human approval, never auto-merge


#: Paths where a wrong change costs money, credentials, or customer trust, mapped
#: to why. Glob-matched against repository-relative paths. Every entry here is a
#: place where "the tests passed" is not sufficient evidence of safety, either
#: because the blast radius is outside the repository (infrastructure, payouts) or
#: because the thing that would catch the mistake is what is being changed (CI,
#: auth, migrations).
PROTECTED_PATHS: dict[str, str] = {
    ".github/workflows/**": "CI/CD definition — changing it changes what checks the next change faces",
    ".github/actions/**": "composite action used by CI",
    ".github/dependabot.yml": "dependency update policy",
    "CODEOWNERS": "who must review what",
    ".github/CODEOWNERS": "who must review what",
    # Dependency manifests: a resolved lockfile is remote code that will execute
    # in CI and in production.
    "**/package-lock.json": "dependency lockfile — pulls third-party code into the build",
    "**/pnpm-lock.yaml": "dependency lockfile — pulls third-party code into the build",
    "**/yarn.lock": "dependency lockfile — pulls third-party code into the build",
    "**/poetry.lock": "dependency lockfile — pulls third-party code into the build",
    "**/requirements*.txt": "dependency manifest — pulls third-party code into the build",
    "**/pyproject.toml": "dependency and build configuration",
    "**/package.json": "dependency and build configuration",
    # Money. Every path the control plane uses to price, charge, refund or ship.
    "control-plane/app/payments.py": "payment processing",
    "control-plane/app/paypal.py": "payment processing",
    "control-plane/app/pricebook.py": "server-side price authority",
    "control-plane/app/order_ledger.py": "revenue booking and idempotency",
    "control-plane/app/fulfillment.py": "fulfillment state machine",
    "control-plane/app/printful.py": "supplier orders — spends money",
    "control-plane/app/etsy*.py": "live marketplace writes",
    "control-plane/app/governance.py": "the approval gate itself",
    "control-plane/app/security.py": "admin authentication and rate limiting",
    "control-plane/app/audit.py": "the audit ledger",
    "control-plane/app/routers/**": "API surface, including checkout and webhooks",
    "control-plane/app/data/pricebook.json": "live prices",
    "control-plane/migrations/**": "database schema — forward-only, hard to reverse",
    "data/store/catalog.json": "live catalogue with payment links",
    "data/side-store/catalog.json": "live catalogue",
    # Infrastructure and secrets.
    "**/Dockerfile": "runtime image",
    "docker-compose*.yml": "service topology",
    "render.yaml": "deployment configuration",
    "**/*.tf": "infrastructure as code",
    "CNAME": "domain routing",
    "_headers": "security headers served to every visitor",
    "_redirects": "routing served to every visitor",
    ".env*": "environment configuration",
    # Statements the business is held to.
    "LICENSE*": "licensing terms",
    "SECURITY.md": "published security policy",
    "privacy*.html": "published privacy policy",
    "terms*.html": "published terms",
    "refund*.html": "published refund policy",
}

#: Substrings in a path that mark payment/auth/fulfillment code wherever it lives,
#: so a new module under a new directory is protected the day it is added rather
#: than the day someone remembers to extend the table above.
PROTECTED_NAME_MARKERS = (
    "payment",
    "paypal",
    "stripe",
    "checkout",
    "webhook",
    "refund",
    "payout",
    "pricing",
    "pricebook",
    "invoice",
    "billing",
    "fulfillment",
    "auth",
    "session",
    "credential",
    "secret",
    "token",
    "migration",
)

#: Path patterns a bot may change on its own, once every required check is green.
#: Narrow on purpose: this is the complete list of things that cannot break a
#: customer transaction, and it is meant to stay boring.
AUTO_MERGEABLE_PATHS: dict[str, str] = {
    "docs/**/*.md": "documentation",
    "*.md": "documentation",
    "tests/**": "tests only — cannot change production behaviour",
    "**/tests/**": "tests only — cannot change production behaviour",
    ".github/ISSUE_TEMPLATE/**": "issue templates",
    "operations/**": "generated reports",
}


@dataclass
class ChangeAssessment:
    """How a proposed change is classified, and why."""

    risk: ChangeRisk
    may_auto_merge: bool
    paths: list[str]
    protected: dict[str, str] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": POLICY_VERSION,
            "risk": self.risk.value,
            "may_auto_merge": self.may_auto_merge,
            "paths": self.paths,
            "protected": self.protected,
            "reasons": self.reasons,
        }


def _matches(path: str, pattern: str) -> bool:
    """Glob match that treats ``**`` as crossing directory separators."""
    # Strip a leading "./" only. `lstrip("./")` would strip every leading dot and
    # slash, turning ".github/workflows/ci.yml" into "github/workflows/ci.yml" and
    # ".env" into "env" — which silently drops every dotfile out of the protected
    # set while the policy still reports itself as enforcing.
    normalized = path[2:] if path.startswith("./") else path
    if fnmatch.fnmatch(normalized, pattern):
        return True
    # fnmatch does not special-case `**`, so `a/**` misses `a/b/c`. Compare against
    # the prefix form too.
    if pattern.endswith("/**"):
        return normalized.startswith(pattern[:-2])
    if pattern.startswith("**/"):
        tail = pattern[3:]
        return fnmatch.fnmatch(normalized, tail) or any(
            fnmatch.fnmatch(normalized[i:], tail) for i in range(len(normalized)) if normalized[i - 1: i] == "/"
        )
    return False


def protected_reason(path: str) -> str | None:
    """Why this path is protected, or ``None`` if it is not."""
    for pattern, reason in PROTECTED_PATHS.items():
        if _matches(path, pattern):
            return reason
    lowered = path.lower()
    for marker in PROTECTED_NAME_MARKERS:
        # Match the filename, not the whole path: `docs/payments.md` is
        # documentation about payments, not payment code.
        if marker in Path(lowered).name:
            return f"filename names a protected concern ({marker})"
    return None


def is_auto_mergeable_path(path: str) -> bool:
    """True when a path is on the narrow always-safe list."""
    return any(_matches(path, pattern) for pattern in AUTO_MERGEABLE_PATHS)


def classify_change(paths: list[str]) -> ChangeAssessment:
    """Classify a proposed change by the paths it touches.

    A change is auto-mergeable only when **every** path it touches is on the
    narrow safe list. One protected file in an otherwise-trivial diff makes the
    whole change HIGH — a change is merged as a unit, so it is only as safe as its
    riskiest file.

    An empty change is MEDIUM, not LOW: something that reports touching nothing is
    a broken caller, and a broken caller is not evidence of safety.
    """
    cleaned = [p.strip() for p in paths if p and p.strip()]
    if not cleaned:
        return ChangeAssessment(
            risk=ChangeRisk.MEDIUM,
            may_auto_merge=False,
            paths=[],
            reasons=["no paths supplied — cannot establish what would change (fail closed)"],
        )

    protected = {path: reason for path in cleaned if (reason := protected_reason(path))}
    if protected:
        return ChangeAssessment(
            risk=ChangeRisk.HIGH,
            may_auto_merge=False,
            paths=cleaned,
            protected=protected,
            reasons=[
                f"{path}: {reason}" for path, reason in sorted(protected.items())
            ]
            + ["protected paths require a pull request and human approval"],
        )

    unlisted = [path for path in cleaned if not is_auto_mergeable_path(path)]
    if unlisted:
        return ChangeAssessment(
            risk=ChangeRisk.MEDIUM,
            may_auto_merge=False,
            paths=cleaned,
            reasons=[
                "changes production behaviour outside the auto-merge allow-list: "
                + ", ".join(sorted(unlisted)[:10]),
                "pull request + human approval required",
            ],
        )

    return ChangeAssessment(
        risk=ChangeRisk.LOW,
        may_auto_merge=True,
        paths=cleaned,
        reasons=["every path is documentation, tests or generated reports"],
    )


# ── Circuit breakers ───────────────────────────────────────────────────────

#: At most one automated merge lands per day. The limit is not about volume, it is
#: about attribution: when something breaks, one automated change per day can be
#: correlated with it by eye.
MAX_AUTO_MERGES_PER_DAY = 1

#: More than this many open bot pull requests means the queue is not being read,
#: and opening another adds noise rather than value.
MAX_OPEN_BOT_PRS = 3

#: Two consecutive failed deployments means the thing being deployed is broken in a
#: way the pipeline did not catch. Automated change stops until a human has looked.
MAX_CONSECUTIVE_DEPLOY_FAILURES = 2

#: Gates whose failure halts *all* automated mutation. Each one means the evidence
#: an automated decision would rely on is untrustworthy.
HALT_ALL_SIGNALS = {
    "secret_scan_passing": "a secret may be exposed — no automated change until it is cleared",
    "critical_vulnerability_scan_passing": "an unpatched critical vulnerability is present",
    "payment_tests_passing": "the payment safety tests are red",
    "production_health_passing": "production is unhealthy",
}

#: Gates whose failure halts revenue-side automation only. The repository can still
#: be maintained; nothing may touch orders, listings or inventory.
HALT_REVENUE_SIGNALS = {
    "webhook_verification_passing": "webhook signature verification is failing",
    "order_reconciliation_passing": "orders and payments do not reconcile",
    "inventory_reconciliation_passing": "inventory does not reconcile",
    "fulfillment_checks_passing": "fulfillment checks are failing",
}


@dataclass
class BreakerDecision:
    """Whether automation may act, and what is stopping it."""

    mutation_allowed: bool
    revenue_automation_allowed: bool
    auto_merge_allowed: bool
    blocked_by: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": POLICY_VERSION,
            "mutation_allowed": self.mutation_allowed,
            "revenue_automation_allowed": self.revenue_automation_allowed,
            "auto_merge_allowed": self.auto_merge_allowed,
            "blocked_by": self.blocked_by,
        }


def evaluate_breakers(state: dict[str, Any]) -> BreakerDecision:
    """Decide whether automation may act at all, from observed state.

    ``state`` is a plain dict a workflow assembles (counts and booleans). Every
    health signal defaults to **False** when absent: "we did not check" and "the
    check failed" are the same thing to a system deciding whether to change itself
    unattended. That is the opposite of convenient and it is the point — the
    common way a breaker stops working is that the signal feeding it quietly
    disappears and the breaker reads the absence as "fine".
    """
    blocked: list[str] = []

    for signal, why in HALT_ALL_SIGNALS.items():
        if state.get(signal) is not True:
            observed = "not reported" if signal not in state else "failing"
            blocked.append(f"{signal} [{observed}]: {why}")
    halt_all = bool(blocked)

    revenue_blocked: list[str] = []
    for signal, why in HALT_REVENUE_SIGNALS.items():
        if state.get(signal) is not True:
            observed = "not reported" if signal not in state else "failing"
            revenue_blocked.append(f"{signal} [{observed}]: {why}")

    consecutive_failures = int(state.get("consecutive_deploy_failures", 0) or 0)
    if consecutive_failures >= MAX_CONSECUTIVE_DEPLOY_FAILURES:
        blocked.append(
            f"consecutive_deploy_failures={consecutive_failures} "
            f"(limit {MAX_CONSECUTIVE_DEPLOY_FAILURES}): roll back and investigate before "
            "changing anything else"
        )
        halt_all = True

    open_bot_prs = int(state.get("open_bot_prs", 0) or 0)
    merges_today = int(state.get("auto_merges_today", 0) or 0)

    auto_merge_blocked: list[str] = []
    if merges_today >= MAX_AUTO_MERGES_PER_DAY:
        auto_merge_blocked.append(
            f"auto_merges_today={merges_today} (limit {MAX_AUTO_MERGES_PER_DAY})"
        )
    if open_bot_prs >= MAX_OPEN_BOT_PRS:
        auto_merge_blocked.append(f"open_bot_prs={open_bot_prs} (limit {MAX_OPEN_BOT_PRS})")

    blocked.extend(auto_merge_blocked)
    blocked.extend(revenue_blocked)

    return BreakerDecision(
        mutation_allowed=not halt_all,
        revenue_automation_allowed=not halt_all and not revenue_blocked,
        auto_merge_allowed=not halt_all and not auto_merge_blocked,
        blocked_by=blocked,
    )


def may_auto_merge(paths: list[str], state: dict[str, Any]) -> tuple[bool, list[str]]:
    """The whole question in one call: may a bot merge this change, right now?

    Both gates must pass. A trivial documentation fix is still refused while a
    secret scan is red, and a green repository still does not license a change to
    a payment path.
    """
    assessment = classify_change(paths)
    decision = evaluate_breakers(state)
    if assessment.may_auto_merge and decision.auto_merge_allowed:
        return True, []
    reasons = []
    if not assessment.may_auto_merge:
        reasons.extend(assessment.reasons)
    if not decision.auto_merge_allowed:
        reasons.extend(decision.blocked_by)
    return False, reasons


# ── Self-check ─────────────────────────────────────────────────────────────

#: Invariants that must hold for this policy to mean anything. Run in CI and
#: before any automated merge, in the spirit of the RFED bot's ``--self-check``:
#: a policy module that has been edited into uselessness should say so out loud.
SELF_CHECKS: list[tuple[str, Any]] = [
    (
        "a workflow change is never auto-mergeable",
        lambda: not classify_change([".github/workflows/ci.yml"]).may_auto_merge,
    ),
    (
        "a payment module change is never auto-mergeable",
        lambda: not classify_change(["control-plane/app/payments.py"]).may_auto_merge,
    ),
    (
        "a price book change is never auto-mergeable",
        lambda: not classify_change(["control-plane/app/data/pricebook.json"]).may_auto_merge,
    ),
    (
        "a lockfile change is never auto-mergeable",
        lambda: not classify_change(["storefront/package-lock.json"]).may_auto_merge,
    ),
    (
        "a migration is never auto-mergeable",
        lambda: not classify_change(["control-plane/migrations/006_x.sql"]).may_auto_merge,
    ),
    (
        "one protected file poisons an otherwise-safe change",
        lambda: not classify_change(
            ["docs/NOTES.md", "README.md", "control-plane/app/security.py"]
        ).may_auto_merge,
    ),
    (
        "an unknown path is not auto-mergeable",
        lambda: not classify_change(["some/new/module.py"]).may_auto_merge,
    ),
    (
        "an empty change is not auto-mergeable",
        lambda: not classify_change([]).may_auto_merge,
    ),
    (
        "a documentation-only change is auto-mergeable",
        lambda: classify_change(["docs/RUNBOOK.md"]).may_auto_merge,
    ),
    (
        "missing health signals block mutation",
        lambda: not evaluate_breakers({}).mutation_allowed,
    ),
    (
        "a red secret scan halts all mutation",
        lambda: not evaluate_breakers({**_HEALTHY, "secret_scan_passing": False}).mutation_allowed,
    ),
    (
        "two failed deploys halt all mutation",
        lambda: not evaluate_breakers(
            {**_HEALTHY, "consecutive_deploy_failures": 2}
        ).mutation_allowed,
    ),
    (
        "a failing reconciliation halts revenue automation only",
        lambda: (
            lambda d: d.mutation_allowed and not d.revenue_automation_allowed
        )(evaluate_breakers({**_HEALTHY, "order_reconciliation_passing": False})),
    ),
    (
        "the daily auto-merge budget is enforced",
        lambda: not evaluate_breakers({**_HEALTHY, "auto_merges_today": 1}).auto_merge_allowed,
    ),
    (
        "the open bot PR ceiling is enforced",
        lambda: not evaluate_breakers({**_HEALTHY, "open_bot_prs": 3}).auto_merge_allowed,
    ),
    (
        "a healthy repository can auto-merge a documentation fix",
        lambda: may_auto_merge(["docs/RUNBOOK.md"], _HEALTHY)[0],
    ),
]

#: Every gate green and no budget spent — the only state in which anything merges.
_HEALTHY: dict[str, Any] = {
    **{signal: True for signal in HALT_ALL_SIGNALS},
    **{signal: True for signal in HALT_REVENUE_SIGNALS},
    "consecutive_deploy_failures": 0,
    "open_bot_prs": 0,
    "auto_merges_today": 0,
}


def run_self_check() -> tuple[bool, list[str]]:
    """Verify the policy still refuses what it claims to refuse."""
    failures = []
    for description, check in SELF_CHECKS:
        try:
            if not check():
                failures.append(description)
        except Exception as exc:  # a policy that crashes is a policy that is not enforcing
            failures.append(f"{description} (raised {type(exc).__name__}: {exc})")
    return not failures, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-check", action="store_true", help="verify the policy invariants")
    parser.add_argument("--paths", nargs="*", default=None, help="classify a change by path")
    parser.add_argument("--state", help="JSON file of observed state for the circuit breakers")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.self_check:
        ok, failures = run_self_check()
        if args.json:
            print(json.dumps({"self_check": "pass" if ok else "fail", "failures": failures}, indent=2))
        else:
            print(f"automation policy v{POLICY_VERSION}: {len(SELF_CHECKS)} invariants")
            for failure in failures:
                print(f"  FAIL  {failure}")
            print("  all invariants hold" if ok else f"  {len(failures)} invariant(s) violated")
        return 0 if ok else 1

    state: dict[str, Any] = {}
    if args.state:
        try:
            state = json.loads(Path(args.state).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"could not read state: {exc}", file=sys.stderr)
            return 2  # unreadable state is not "healthy"

    if args.paths is not None:
        allowed, reasons = may_auto_merge(args.paths, state)
        assessment = classify_change(args.paths)
        report = {
            **assessment.to_dict(),
            "auto_merge_allowed": allowed,
            "blocked_by": reasons,
        }
        print(json.dumps(report, indent=2) if args.json else _render_change(report))
        return 0 if allowed else 1

    decision = evaluate_breakers(state)
    print(json.dumps(decision.to_dict(), indent=2) if args.json else _render_breakers(decision))
    return 0 if decision.mutation_allowed else 1


def _render_change(report: dict[str, Any]) -> str:
    lines = [
        f"risk: {report['risk'].upper()}",
        f"auto-merge: {'ALLOWED' if report['auto_merge_allowed'] else 'REFUSED'}",
    ]
    # blocked_by repeats the classification reasons when the paths are what
    # refused the change; show each reason once.
    seen: set[str] = set()
    for reason in report["reasons"] + report["blocked_by"]:
        if reason not in seen:
            seen.add(reason)
            lines.append(f"  - {reason}")
    return "\n".join(lines)


def _render_breakers(decision: BreakerDecision) -> str:
    lines = [
        f"mutation:           {'ALLOWED' if decision.mutation_allowed else 'HALTED'}",
        f"revenue automation: {'ALLOWED' if decision.revenue_automation_allowed else 'HALTED'}",
        f"auto-merge:         {'ALLOWED' if decision.auto_merge_allowed else 'HALTED'}",
    ]
    lines += [f"  - {reason}" for reason in decision.blocked_by]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
