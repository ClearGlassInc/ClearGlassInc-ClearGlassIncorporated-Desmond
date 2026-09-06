# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Defender response layer — auto-quarantine.

Quarantine here means *advisory containment*, not deletion. The module builds a
tamper-evident incident record for the findings that warrant containment and
recommends the response actions defined in the policy. It deliberately never
modifies, deletes, disables, or rewrites repository content: enforcement is the
job of branch protection, required reviews, and humans acting on this record.

Outputs (operations/output/defender/):
  - quarantine.json   structured incident record with per-file SHA-256
  - quarantine.md     human-readable containment brief

In GitHub Actions it also emits ::error::/::warning:: annotations and appends a
summary to $GITHUB_STEP_SUMMARY so findings surface on the run without any
write access to the repository.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bots.defender import policy as policy_mod

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from bots.defender.engine import DefenderReport, Finding

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "operations" / "output" / "defender"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str | None:
    """SHA-256 of a repo file, for chain-of-custody on quarantined files."""
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(65536), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def _containable(report: "DefenderReport", policy: dict[str, Any]) -> list["Finding"]:
    """Findings at or above the containment threshold (default critical+high)."""
    gate = set(policy.get("enforcement", {}).get("quarantine_on", ["critical", "high"]))
    return [f for f in report.findings if f.severity in gate]


def _incident(finding: "Finding", policy: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "rule_id": finding.rule_id,
        "category": finding.category,
        "severity": finding.severity,
        "title": finding.title,
        "file": finding.file,
        "line": finding.line,
        "evidence": finding.evidence,
        "recommended_actions": policy_mod.response_actions(finding.severity, policy),
        "status": "flagged_for_review",
        "enforcement": "advisory",
    }
    if finding.file:
        record["file_sha256"] = _sha256(ROOT / finding.file)
    return record


def _emit_ci_annotations(findings: list["Finding"]) -> None:
    """Surface findings as GitHub Actions annotations when running in CI."""
    if os.getenv("GITHUB_ACTIONS", "").lower() != "true":
        return
    for f in findings:
        stream = "error" if f.severity == "critical" else "warning"
        loc = ""
        if f.file:
            loc = f"file={f.file}" + (f",line={f.line}" if f.line else "")
        prefix = f"::{stream} {loc}::" if loc else f"::{stream}::"
        print(f"{prefix}[defender:{f.rule_id}] {f.title}")

    summary_path = os.getenv("GITHUB_STEP_SUMMARY", "").strip()
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write(f"\n### 🛡️ Defender quarantine — {len(findings)} item(s)\n\n")
                for f in findings:
                    loc = f.file + (f":{f.line}" if f.line else "")
                    fh.write(f"- **{f.severity}** `{f.rule_id}` `{loc}` — {f.title}\n")
        except OSError:
            pass


def _render_markdown(record: dict[str, Any]) -> str:
    md = [
        "# ClearGlass Defender — Quarantine Record",
        "",
        f"- Run (UTC): {record['run_utc']}",
        f"- Repository: `{record['repo']}`",
        f"- Quarantined items: {record['quarantined']}",
        "- Enforcement: **advisory** (no files were modified or deleted)",
        "",
        "> Quarantine is a review gate, not a destructive action. Enforce the "
        "response plan through branch protection, required reviews, and token rotation.",
        "",
        "## Incidents",
        "",
    ]
    if not record["incidents"]:
        md.append("None. ✅")
    for inc in record["incidents"]:
        loc = inc["file"] + (f":{inc['line']}" if inc["line"] else "")
        md.append(f"### {inc['severity'].upper()} — {inc['title']}")
        md.append("")
        md.append(f"- Rule: `{inc['rule_id']}` ({inc['category']})")
        if loc:
            md.append(f"- Location: `{loc}`")
        if inc.get("file_sha256"):
            md.append(f"- File SHA-256: `{inc['file_sha256']}`")
        md.append(f"- Recommended actions: {', '.join(f'`{a}`' for a in inc['recommended_actions'])}")
        md.append(f"- Status: `{inc['status']}` (enforcement: {inc['enforcement']})")
        md.append("")
    return "\n".join(md)


def quarantine(
    report: "DefenderReport",
    policy: dict[str, Any] | None = None,
    *,
    emit_ci_annotations: bool = True,
) -> dict[str, Any]:
    """Build the advisory containment record and write it to disk.

    Non-destructive: returns and persists a record; never touches the flagged
    files themselves. Returns the record manifest.
    """
    policy = policy or policy_mod.load_policy()
    findings = _containable(report, policy)
    incidents = [_incident(f, policy) for f in findings]

    record: dict[str, Any] = {
        "run_utc": _now(),
        "repo": report.repo,
        "enforcement": "advisory",
        "quarantined": len(incidents),
        "response_plan": report.response_plan,
        "incidents": incidents,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "quarantine.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "quarantine.md").write_text(_render_markdown(record), encoding="utf-8")

    # Unit tests exercise intentionally dangerous fixtures.  Callers must opt
    # out explicitly for those synthetic reports; genuine scans retain the
    # fail-visible CI annotations by default.
    if emit_ci_annotations:
        _emit_ci_annotations(findings)
    return record
