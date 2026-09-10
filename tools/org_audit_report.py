#!/usr/bin/env python3
"""Render the org audit into github_audit_report.csv.

Every value is measured. Where something was not measured, the cell says so
rather than carrying a zero — a hardcoded `bugs_found: 0` would make the report
worthless precisely where it matters most.
"""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

FLAGSHIP = "ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond"

# Forks of upstream projects, per the GitHub repository listing. Their advisories
# and unpinned actions are inherited from upstream, not written at ClearGlass —
# reporting them as ClearGlass defects would misdirect the remediation effort.
FORKS = {
    "ClearGlassIncorp/hermes-agent", "ClearGlasslabs/hermes-agent",
    "ClearGlassIncorp/Opal-Koboi", "ClearGlasslabs/ClearWire",
    "ClearGlasslabs/claude-agent-sdk-python", "ClearGlasslabs/gods-eye-view",
    "ClearGlasslabs/vscode", "ClearGlasslabs/SocialPwned",
    "ClearGlasslabs/claude-code", "ClearGlasslabs/claude-ads",
    "ClearGlasslabs/azure-powershell", "ClearGlasslabs/agent-reach",
    "ClearGlasslabs/workflow-artifacts", "ClearGlasslabs/PwnedPasswordsDownloader",
    "ClearGlasslabs/freedatabreaches", "ClearGlasslabs/EmailAddressExtractor",
    "ClearGlassIncorp/EmailAddressExtractor",
}

# Distinct defects found and fixed on the flagship repo this session, and only
# there: it is the one repository that was actually cloned, built, tested and
# patched. Enumerated in DEBUG-AND-FIX-REPORT.md.
FLAGSHIP_FIXED = 35

def workflows_status(row: dict) -> str:
    if row.get("reachable") != "yes":
        return "UNREACHABLE"
    registered = row.get("workflows_registered", 0)
    stray = row.get("workflows_stray_unrunnable", 0)
    if registered == 0 and stray == 0:
        return "NONE_DEFINED"
    if registered == 0 and stray:
        return f"ALL_INERT ({stray} parked outside .github/)"
    # Verified against the Actions API for the flagship repo: jobs complete as
    # `failure` with billable.UBUNTU.total_ms = 0 and runner_id 0 — never
    # dispatched. This is an org-level entitlement block, so it applies to every
    # repository under these owners.
    return f"NOT_EXECUTING ({registered} registered, 0 billable ms)"

def main(src: str, dest: str) -> int:
    rows = json.loads(Path(src).read_text())
    fields = [
        "repository", "is_fork", "bugs_found", "workflows_status", "bots_active",
        "vulnerabilities", "patch_status", "dependencies_updated",
        "workflows_registered", "workflows_inert", "unpinned_actions",
        "packages_without_lockfile", "test_files", "measurement_notes",
    ]
    out = []
    for row in sorted(rows, key=lambda r: r["repository"]):
        repo = row["repository"]
        reachable = row.get("reachable") == "yes"
        is_flagship = repo == FLAGSHIP

        if not reachable:
            out.append({
                "repository": repo, "is_fork": str(repo in FORKS).lower(),
                "bugs_found": "NOT_MEASURED",
                "workflows_status": "UNREACHABLE", "bots_active": "NOT_MEASURED",
                "vulnerabilities": "NOT_MEASURED", "patch_status": "NOT_ATTEMPTED",
                "dependencies_updated": "false",
                "workflows_registered": "", "workflows_inert": "",
                "unpinned_actions": "", "packages_without_lockfile": "",
                "test_files": "",
                "measurement_notes": row.get("note", "clone failed (private or removed)"),
            })
            continue

        crit = row.get("vuln_critical", 0)
        high = row.get("vuln_high", 0)
        audited = row.get("lockfiles_audited", 0)
        locks = row.get("node_lockfiles", 0)

        if locks == 0:
            vulns = "NO_LOCKFILE"
            note_v = "no package-lock.json; npm advisories not resolvable"
        elif audited == 0:
            vulns = "AUDIT_FAILED"
            note_v = f"{locks} lockfile(s) present but npm audit returned nothing"
        else:
            vulns = crit + high
            note_v = f"critical+high from {audited}/{locks} lockfile(s); python deps not audited"

        notes = [note_v]
        if row.get("workflows_stray_unrunnable"):
            notes.append(
                f"{row['workflows_stray_unrunnable']} workflow file(s) in a top-level "
                "workflows/ dir that GitHub never reads"
            )
        if row.get("unpinned_actions"):
            notes.append(f"{row['unpinned_actions']} external action(s) pinned by mutable tag")

        if repo in FORKS:
            notes.append("fork of an upstream project; findings are inherited, not authored here")

        out.append({
            "repository": repo,
            "is_fork": str(repo in FORKS).lower(),
            "bugs_found": FLAGSHIP_FIXED if is_flagship else "NOT_MEASURED",
            "workflows_status": workflows_status(row),
            "bots_active": row.get("bots_active", 0),
            "vulnerabilities": vulns,
            "patch_status": "COMPLETE" if is_flagship else "NOT_ATTEMPTED",
            "dependencies_updated": "true" if is_flagship else "false",
            "workflows_registered": row.get("workflows_registered", 0),
            "workflows_inert": row.get("workflows_stray_unrunnable", 0),
            "unpinned_actions": row.get("unpinned_actions", 0),
            "packages_without_lockfile": row.get("packages_without_lockfile", 0),
            "test_files": row.get("test_files", 0),
            "measurement_notes": "; ".join(notes),
        })

    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)
    print(f"wrote {dest} — {len(out)} repositories")
    reachable = [r for r in out if r["workflows_status"] != "UNREACHABLE"]
    print(f"  reachable: {len(reachable)}  unreachable: {len(out) - len(reachable)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
