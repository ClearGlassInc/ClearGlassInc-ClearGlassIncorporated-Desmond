# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Defender policy layer.

Loads the JSON policy (bots/config/defender_policy.json) and exposes the pure
decision functions the engine and response layers rely on: severity ranking,
allowlist matching, response-action mapping, and build-gate evaluation.

This module never imports the engine, so it stays free of side effects and the
package has no import cycle. It operates on findings by attribute access
(`finding.severity`, `finding.file`), so any object with those fields works.
"""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from bots.defender.engine import Finding

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = ROOT / "bots" / "config" / "defender_policy.json"

SEVERITY_RANK: dict[str, int] = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}
SEVERITIES: tuple[str, ...] = ("critical", "high", "medium", "low", "info")


def load_policy(path: str | Path | None = None) -> dict[str, Any]:
    """Read and parse the JSON policy. Falls back to the bundled default path."""
    policy_path = Path(path) if path else DEFAULT_POLICY_PATH
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Defender policy must be a JSON object: {policy_path}")
    return data


def rank(severity: str) -> int:
    """Numeric ordering for a severity label (unknown labels sort lowest)."""
    return SEVERITY_RANK.get(severity, 0)


def max_severity(findings: Iterable["Finding"]) -> str:
    """Highest severity present in a set of findings, or 'info' if empty."""
    best = "info"
    for finding in findings:
        if rank(finding.severity) > rank(best):
            best = finding.severity
    return best


def is_allowlisted(rel_path: str, policy: dict[str, Any]) -> bool:
    """True when a repo-relative path is exempt from scanning per policy.

    Supports both directory/prefix entries ("downloads/") and glob entries
    ("**/*.example.json"). Matching is done on the POSIX-style path.
    """
    posix = rel_path.replace("\\", "/")
    name = posix.rsplit("/", 1)[-1]
    for entry in policy.get("scan", {}).get("allowlist_paths", []):
        pattern = str(entry).replace("\\", "/")
        if pattern.endswith("/") and (posix == pattern[:-1] or posix.startswith(pattern)):
            return True
        if fnmatch.fnmatch(posix, pattern):
            return True
        # "**/" should also match at depth 0 (fnmatch's * requires a slash here).
        if pattern.startswith("**/") and fnmatch.fnmatch(posix, pattern[3:]):
            return True
        if "/" not in pattern:
            # A bare token matches a path segment; a bare glob matches the basename.
            if pattern in posix.split("/") or fnmatch.fnmatch(name, pattern):
                return True
    return False


def response_actions(severity: str, policy: dict[str, Any]) -> list[str]:
    """Ordered response actions configured for a severity label."""
    actions = policy.get("severity_actions", {}).get(severity, [])
    return [str(a) for a in actions]


def response_plan(findings: Iterable["Finding"], policy: dict[str, Any]) -> list[str]:
    """De-duplicated, severity-ordered union of response actions for all findings."""
    plan: list[str] = []
    by_rank = sorted(findings, key=lambda f: rank(f.severity), reverse=True)
    for finding in by_rank:
        for action in response_actions(finding.severity, policy):
            if action not in plan:
                plan.append(action)
    return plan


def severity_counts(findings: Iterable["Finding"]) -> dict[str, int]:
    """Count of findings per severity, always including every known label."""
    counts = {sev: 0 for sev in SEVERITIES}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def should_fail_build(findings: Iterable["Finding"], policy: dict[str, Any]) -> bool:
    """True when any finding's severity is in enforcement.fail_build_on."""
    gate = set(policy.get("enforcement", {}).get("fail_build_on", ["critical"]))
    return any(finding.severity in gate for finding in findings)


def should_open_issue(findings: Iterable["Finding"], policy: dict[str, Any]) -> bool:
    """True when any finding warrants opening a tracking/incident issue."""
    gate = set(policy.get("enforcement", {}).get("open_issue_on", ["critical", "high"]))
    return any(finding.severity in gate for finding in findings)
