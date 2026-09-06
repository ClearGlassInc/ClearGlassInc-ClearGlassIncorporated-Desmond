# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Defender engine — the sensor layer and orchestrator.

Three responsibilities:

  1. Sensor   — scan workflows, secrets, dependencies, and command surfaces and
                emit structured Findings (engine.scan_*).
  2. Correlate — combine related findings into higher-severity incidents
                (engine.correlate).
  3. Orchestrate — apply the policy, assemble the report, and drive the response
                layer (engine.run / engine.main).

Pure stdlib, no third-party imports — consistent with the rest of bots/. The
report is written to operations/output/defender/ and the response layer
(alerting + quarantine) is invoked from run().
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bots.defender import policy as policy_mod

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "operations" / "output" / "defender"
WORKFLOW_DIR = ROOT / ".github" / "workflows"

GITHUB_REPO = "clearglassinc/clearglassinc.github.io"

# A fully pinned action ref is a 40-character hex commit SHA.
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_USES_RE = re.compile(r"^\s*-?\s*uses:\s*(?P<ref>\S+)")
_PERMISSIONS_RE = re.compile(r"(?m)^\s*permissions:")
_WRITE_ALL_RE = re.compile(r"(?m)^\s*permissions:\s*write-all\b")
# pull_request_target as a real YAML trigger (mapping key or list item), not
# a mention inside a comment or string.
_PR_TARGET_RE = re.compile(r"(^|[\s\[,])pull_request_target(\s*:|\s*[\],]|\s*$)")
_EVIDENCE_MAX = 160


@dataclass
class Finding:
    """A single defensive-security observation."""

    rule_id: str
    category: str  # workflow | secret | dependency | command | correlation
    severity: str  # info | low | medium | high | critical
    title: str
    detail: str
    file: str = ""
    line: int = 0
    evidence: str = ""


@dataclass
class DefenderReport:
    """The full result of one defender run."""

    run_utc: str
    repo: str
    scanned_files: int
    summary: dict[str, int]
    response_plan: list[str]
    fail_build: bool
    findings: list[Finding] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _rel_to(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _rel(path: Path) -> str:
    return _rel_to(path, ROOT)


def _read_text(path: Path, policy: dict[str, Any]) -> str | None:
    max_bytes = int(policy.get("scan", {}).get("max_file_bytes", 2_097_152))
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _truncate(text: str) -> str:
    snippet = text.strip()
    return snippet if len(snippet) <= _EVIDENCE_MAX else snippet[:_EVIDENCE_MAX] + "…"


def _redact(text: str) -> str:
    """Mask the body of a suspected secret so the report never leaks it."""
    stripped = text.strip()
    if len(stripped) <= 8:
        return "****"
    return f"{stripped[:4]}…{stripped[-2:]} (redacted)"


def iter_files(root: Path, extensions: set[str], policy: dict[str, Any]) -> list[Path]:
    """Repo files matching the given extensions, minus excluded/allowlisted paths."""
    exclude = set(policy.get("scan", {}).get("exclude_dirs", []))
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        rel = _rel_to(path, root)
        parts = set(rel.split("/"))
        if parts & exclude:
            continue
        if policy_mod.is_allowlisted(rel, policy):
            continue
        files.append(path)
    return files


# ── sensor: workflow integrity ────────────────────────────────────────────────


def _action_ref(uses_value: str) -> str | None:
    """Extract the ref after '@' for a third-party action, or None to skip.

    Local actions (./...), reusable local workflows, and docker digest refs are
    not third-party tag risks and are skipped.
    """
    value = uses_value.strip().strip("\"'")
    if value.startswith("./") or value.startswith("../"):
        return None
    if value.startswith("docker://"):
        return None
    if "@" not in value:
        return ""  # third-party action with no ref at all → treat as unpinned
    return value.rsplit("@", 1)[1]


def _uses_pull_request_target(text: str) -> bool:
    """True only when pull_request_target is an actual trigger, ignoring comments."""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0]  # drop inline comment before matching
        if _PR_TARGET_RE.search(line):
            return True
    return False


def scan_workflows(policy: dict[str, Any], wf_dir: Path = WORKFLOW_DIR) -> list[Finding]:
    rules = policy.get("workflow_rules", {})
    contexts = policy.get("injectable_contexts", [])
    findings: list[Finding] = []
    if not wf_dir.exists():
        return findings

    base = wf_dir.parent.parent  # repo root, for clean ".github/workflows/x" paths
    for wf in sorted(wf_dir.glob("*.y*ml")):
        text = _read_text(wf, policy)
        if text is None:
            continue
        rel = _rel_to(wf, base)
        lines = text.splitlines()

        # Permissions hygiene.
        if "require_permissions_block" in rules and not _PERMISSIONS_RE.search(text):
            r = rules["require_permissions_block"]
            findings.append(Finding(
                rule_id="require_permissions_block", category="workflow",
                severity=r["severity"], title=r["title"], detail=r["detail"], file=rel,
            ))
        if "forbid_write_all" in rules and _WRITE_ALL_RE.search(text):
            r = rules["forbid_write_all"]
            findings.append(Finding(
                rule_id="forbid_write_all", category="workflow",
                severity=r["severity"], title=r["title"], detail=r["detail"], file=rel,
            ))

        # Action pinning.
        for idx, raw in enumerate(lines, start=1):
            match = _USES_RE.match(raw)
            if not match:
                continue
            ref = _action_ref(match.group("ref"))
            if ref is None or _SHA_RE.match(ref):
                continue  # local/docker-digest action, or already SHA-pinned
            rule_key = (
                "forbid_latest_ref" if ref in ("latest", "main", "master")
                else "require_sha_pinned_actions"
            )
            r = rules.get(rule_key) or rules.get("require_sha_pinned_actions")
            if r:
                findings.append(Finding(
                    rule_id=rule_key, category="workflow", severity=r["severity"],
                    title=r["title"], detail=r["detail"], file=rel, line=idx,
                    evidence=_truncate(raw),
                ))

        # Dangerous trigger.
        if "flag_pull_request_target" in rules and _uses_pull_request_target(text):
            r = rules["flag_pull_request_target"]
            findings.append(Finding(
                rule_id="flag_pull_request_target", category="workflow",
                severity=r["severity"], title=r["title"], detail=r["detail"], file=rel,
            ))

        # Script injection via untrusted context in a run step.
        if "forbid_script_injection" in rules:
            for idx, raw in enumerate(lines, start=1):
                if "${{" not in raw:
                    continue
                hit = next((ctx for ctx in contexts if ctx in raw), None)
                if hit:
                    r = rules["forbid_script_injection"]
                    findings.append(Finding(
                        rule_id="forbid_script_injection", category="workflow",
                        severity=r["severity"], title=r["title"],
                        detail=f"{r['detail']} (context: {hit})", file=rel, line=idx,
                        evidence=_truncate(raw),
                    ))

    return findings


# ── sensor: secret exposure ───────────────────────────────────────────────────


def scan_secrets(policy: dict[str, Any], root: Path = ROOT) -> list[Finding]:
    patterns = [
        (p["id"], p["severity"], p["title"], re.compile(p["pattern"]))
        for p in policy.get("secret_patterns", [])
    ]
    extensions = {e.lower() for e in policy.get("scan", {}).get("code_extensions", [])}
    findings: list[Finding] = []
    for path in iter_files(root, extensions, policy):
        text = _read_text(path, policy)
        if text is None:
            continue
        rel = _rel_to(path, root)
        for idx, raw in enumerate(text.splitlines(), start=1):
            for rule_id, severity, title, rx in patterns:
                m = rx.search(raw)
                if m:
                    findings.append(Finding(
                        rule_id=rule_id, category="secret", severity=severity,
                        title=title, detail="Potential credential committed to the repository.",
                        file=rel, line=idx, evidence=_redact(m.group(0)),
                    ))
    return findings


# ── sensor: suspicious command surface ────────────────────────────────────────


def _in_command_scope(rel: str, policy: dict[str, Any]) -> bool:
    scopes = policy.get("scan", {}).get("command_scan_paths", [])
    return any(rel == s or rel.startswith(s.rstrip("/") + "/") for s in scopes)


def scan_commands(policy: dict[str, Any], root: Path = ROOT) -> list[Finding]:
    patterns = [
        (p["id"], p["severity"], p["title"], re.compile(p["pattern"]))
        for p in policy.get("suspicious_commands", [])
    ]
    extensions = {e.lower() for e in policy.get("scan", {}).get("code_extensions", [])}
    findings: list[Finding] = []
    for path in iter_files(root, extensions, policy):
        rel = _rel_to(path, root)
        if not _in_command_scope(rel, policy):
            continue
        text = _read_text(path, policy)
        if text is None:
            continue
        for idx, raw in enumerate(text.splitlines(), start=1):
            for rule_id, severity, title, rx in patterns:
                if rx.search(raw):
                    findings.append(Finding(
                        rule_id=rule_id, category="command", severity=severity,
                        title=title, detail="Suspicious command pattern in automation surface.",
                        file=rel, line=idx, evidence=_truncate(raw),
                    ))
    return findings


# ── sensor: dependency hygiene ────────────────────────────────────────────────


def scan_dependencies(policy: dict[str, Any], root: Path = ROOT) -> list[Finding]:
    """Surface unpinned runtime dependencies. The workflow runs the real audits
    (pip-audit / npm audit); this is a lightweight, offline pinning check."""
    findings: list[Finding] = []
    for req in sorted(root.rglob("requirements*.txt")):
        rel = _rel_to(req, root)
        if {".git", "node_modules"} & set(rel.split("/")):
            continue
        text = _read_text(req, policy)
        if text is None:
            continue
        for idx, raw in enumerate(text.splitlines(), start=1):
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            if not re.search(r"[=<>~!]", line):
                findings.append(Finding(
                    rule_id="unpinned_python_dependency", category="dependency",
                    severity="low", title="Unpinned Python dependency",
                    detail="Dependency has no version constraint; pin it to a known-good range.",
                    file=rel, line=idx, evidence=_truncate(raw),
                ))
    return findings


# ── correlation ───────────────────────────────────────────────────────────────


def correlate(findings: list[Finding], policy: dict[str, Any]) -> list[Finding]:
    """Combine related findings into higher-severity incidents."""
    rules = policy.get("correlation", {})
    extra: list[Finding] = []
    categories = {f.category for f in findings}

    if "secret_plus_workflow_change" in rules and {"secret", "workflow"} <= categories:
        r = rules["secret_plus_workflow_change"]
        extra.append(Finding(
            rule_id="secret_plus_workflow_change", category="correlation",
            severity=r["severity"], title=r["title"], detail=r["detail"],
        ))

    has_prtarget = any(f.rule_id == "flag_pull_request_target" for f in findings)
    has_injection = any(f.rule_id == "forbid_script_injection" for f in findings)
    if "prtarget_plus_injection" in rules and has_prtarget and has_injection:
        r = rules["prtarget_plus_injection"]
        extra.append(Finding(
            rule_id="prtarget_plus_injection", category="correlation",
            severity=r["severity"], title=r["title"], detail=r["detail"],
        ))

    return extra


# ── report assembly + orchestration ──────────────────────────────────────────


def build_report(policy: dict[str, Any], root: Path = ROOT) -> DefenderReport:
    """Run every sensor, correlate, and assemble the report (no side effects)."""
    findings: list[Finding] = []
    findings += scan_workflows(policy, root / ".github" / "workflows")
    findings += scan_secrets(policy, root)
    findings += scan_commands(policy, root)
    findings += scan_dependencies(policy, root)
    findings += correlate(findings, policy)

    findings.sort(key=lambda f: (-policy_mod.rank(f.severity), f.category, f.file, f.line))

    extensions = {e.lower() for e in policy.get("scan", {}).get("code_extensions", [])}
    scanned = len(iter_files(root, extensions, policy))

    return DefenderReport(
        run_utc=_now(),
        repo=GITHUB_REPO,
        scanned_files=scanned,
        summary=policy_mod.severity_counts(findings),
        response_plan=policy_mod.response_plan(findings, policy),
        fail_build=policy_mod.should_fail_build(findings, policy),
        findings=findings,
    )


def _render_markdown(report: DefenderReport) -> str:
    s = report.summary
    md = [
        "# ClearGlass Defender Report",
        "",
        f"- Run (UTC): {report.run_utc}",
        f"- Repository: `{report.repo}`",
        f"- Files scanned: {report.scanned_files}",
        f"- Build gate: {'❌ FAIL' if report.fail_build else '✅ pass'}",
        "",
        "## Severity summary",
        "",
        "| 🔴 critical | 🟠 high | 🟡 medium | 🔵 low | ⚪ info |",
        "| --- | --- | --- | --- | --- |",
        f"| {s['critical']} | {s['high']} | {s['medium']} | {s['low']} | {s['info']} |",
        "",
    ]
    if report.response_plan:
        md += ["## Response plan", "", *[f"- `{a}`" for a in report.response_plan], ""]
    md += ["## Findings", ""]
    if not report.findings:
        md.append("No findings. ✅")
    else:
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
        for f in report.findings:
            loc = f.file + (f":{f.line}" if f.line else "")
            md.append(f"### {icon.get(f.severity, '•')} {f.severity.upper()} — {f.title}")
            md.append("")
            md.append(f"- Rule: `{f.rule_id}` ({f.category})")
            if loc:
                md.append(f"- Location: `{loc}`")
            if f.evidence:
                md.append(f"- Evidence: `{f.evidence}`")
            md.append(f"- {f.detail}")
            md.append("")
    return "\n".join(md)


def run() -> dict[str, Any]:
    """Full scan + response. Returns a manifest. Never raises on findings.

    Entry point used by scripts/bot_runner.py (which prefers run() over main()),
    so a routine scan with findings does not fail the orchestrator job — the
    dedicated defender-watch workflow is where the policy build gate is applied.
    """
    # Imported here to keep the import graph acyclic and the sensor importable
    # in isolation (tests import scan_* without pulling the response layer).
    from bots.defender import alerting, quarantine

    policy = policy_mod.load_policy()
    report = build_report(policy)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "defender_report.json").write_text(
        _to_json(report), encoding="utf-8"
    )
    (OUTPUT_DIR / "defender_report.md").write_text(
        _render_markdown(report), encoding="utf-8"
    )

    alert_result = alerting.dispatch(report, policy)
    quarantine_result = quarantine.quarantine(report, policy)

    return {
        "run_utc": report.run_utc,
        "scanned_files": report.scanned_files,
        "summary": report.summary,
        "total_findings": len(report.findings),
        "fail_build": report.fail_build,
        "response_plan": report.response_plan,
        "alerting": alert_result,
        "quarantine": quarantine_result,
    }


def _to_json(report: DefenderReport) -> str:
    return json.dumps(asdict(report), indent=2)


def main() -> None:
    """CLI entry point. Exits non-zero per policy.enforcement.fail_build_on."""
    manifest = run()
    s = manifest["summary"]
    print(
        "Defender: "
        f"{manifest['total_findings']} finding(s) across {manifest['scanned_files']} files "
        f"— critical={s['critical']} high={s['high']} medium={s['medium']} "
        f"low={s['low']} info={s['info']}"
    )
    if manifest["response_plan"]:
        print(f"Response plan: {', '.join(manifest['response_plan'])}")
    if manifest["fail_build"]:
        print("Build gate: FAIL (policy.enforcement.fail_build_on triggered)", file=sys.stderr)
        sys.exit(1)
    print("Build gate: pass")


if __name__ == "__main__":
    main()
