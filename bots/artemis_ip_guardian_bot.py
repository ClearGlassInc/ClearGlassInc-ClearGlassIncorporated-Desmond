# ARTEMIS // CLEARGLASS INC.
#
# Copyright (c) 2026 ClearGlass Inc. All rights reserved.
# Original Author and Systems Architect: Desmond Otieno Odhiambo.
#
# This source code is proprietary and confidential to ClearGlass Inc.
# Unauthorized copying, modification, distribution, publication, sublicensing,
# reverse engineering, commercial use, or removal of attribution is prohibited
# except where expressly authorized in writing by ClearGlass Inc.
#
# System: ARTEMIS | Organization: ClearGlass Inc. | Classification: Proprietary
"""ARTEMIS IP Guardian bot.

Audits the repository's intellectual-property and attribution posture:

1. Required governance files exist (LICENSE, NOTICE, SECURITY.md,
   .github/CODEOWNERS, CONTRIBUTING.md, TRADEMARKS.md, docs/PROVENANCE.md,
   docs/IP-POLICY.md).
2. ARTEMIS-owned source files carry the ClearGlass Inc. ownership imprint.
3. ARTEMIS agent configurations are valid JSON and point at an existing
   system prompt file.

The bot only reads the tree and writes its report under
``operations/artemis/``. It never modifies audited files. With ``--strict``
(or ``ARTEMIS_STRICT=1``) any violation exits non-zero so CI fails closed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "artemis"

REQUIRED_GOVERNANCE_FILES = [
    "LICENSE",
    "NOTICE",
    "SECURITY.md",
    ".github/CODEOWNERS",
    "CONTRIBUTING.md",
    "TRADEMARKS.md",
    "docs/PROVENANCE.md",
    "docs/IP-POLICY.md",
]

# Paths owned by the ARTEMIS system whose source files must carry the imprint.
ARTEMIS_SOURCE_GLOBS = [
    "agents/artemis_command_system/*",
    "agents/artemis_ip_guardian/*",
    "bots/artemis_ip_guardian_bot.py",
    "bots/artemis_provenance_bot.py",
]

ATTRIBUTION_MARKERS = ("ClearGlass Inc", "Desmond Otieno Odhiambo")


@dataclass(frozen=True)
class CheckResult:
    check: str
    target: str
    status: str  # "pass" | "fail"
    detail: str = ""


@dataclass
class GuardianReport:
    run_utc: str
    strict: bool
    status: str = "pass"
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, check: str, target: str, ok: bool, detail: str = "") -> None:
        self.checks.append(
            CheckResult(check=check, target=target, status="pass" if ok else "fail", detail=detail)
        )
        if not ok:
            self.status = "fail"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def check_governance_files(report: GuardianReport) -> None:
    for rel in REQUIRED_GOVERNANCE_FILES:
        path = ROOT / rel
        ok = path.is_file() and path.stat().st_size > 0
        report.add("governance-file", rel, ok, "" if ok else "missing or empty")


def check_attribution_headers(report: GuardianReport) -> None:
    for pattern in ARTEMIS_SOURCE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file():
                continue
            try:
                head = path.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError as exc:
                report.add("attribution-header", str(path.relative_to(ROOT)), False, f"unreadable: {exc}")
                continue
            missing = [m for m in ATTRIBUTION_MARKERS if m not in head]
            report.add(
                "attribution-header",
                str(path.relative_to(ROOT)),
                not missing,
                "" if not missing else f"missing markers: {', '.join(missing)}",
            )


def check_agent_configs(report: GuardianReport) -> None:
    for agent_dir in ("agents/artemis_command_system", "agents/artemis_ip_guardian"):
        config_path = ROOT / agent_dir / "agent.json"
        rel = str(config_path.relative_to(ROOT))
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report.add("agent-config", rel, False, f"invalid: {exc}")
            continue
        prompt_rel = config.get("system_prompt_path", "")
        prompt_path = config_path.parent / prompt_rel
        ok = bool(prompt_rel) and prompt_path.is_file()
        report.add(
            "agent-config",
            rel,
            ok,
            "" if ok else f"system_prompt_path {prompt_rel!r} does not resolve to a file",
        )


def render_markdown(report: GuardianReport) -> str:
    lines = [
        "# ARTEMIS IP Guardian Report",
        "",
        "Powered by ARTEMIS — A ClearGlass Inc. Intelligence System.",
        "",
        f"- Run (UTC): {report.run_utc}",
        f"- Mode: {'strict (fail closed)' if report.strict else 'report only'}",
        f"- Overall status: **{report.status.upper()}**",
        "",
        "| Check | Target | Status | Detail |",
        "|---|---|---|---|",
    ]
    for c in report.checks:
        lines.append(f"| {c.check} | `{c.target}` | {c.status} | {c.detail} |")
    lines += [
        "",
        "_This report records only checks that actually ran. An attribution",
        "notice establishes authorship but does not by itself prevent theft;",
        "access controls, contracts, licensing, and provenance records are the",
        "enforcing controls (see docs/IP-POLICY.md)._",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ARTEMIS IP Guardian audit")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any violation")
    parser.add_argument("--json", action="store_true", help="print the JSON report to stdout")
    args = parser.parse_args(argv)
    strict = args.strict or os.environ.get("ARTEMIS_STRICT") == "1"

    report = GuardianReport(run_utc=_now_utc(), strict=strict)
    check_governance_files(report)
    check_attribution_headers(report)
    check_agent_configs(report)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "system": "ARTEMIS",
        "organization": "ClearGlass Inc.",
        "bot": "artemis_ip_guardian_bot",
        **asdict(report),
    }
    (OUTPUT_DIR / "ip_guardian_report.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT_DIR / "ip_guardian_report.md").write_text(render_markdown(report), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        failed = [c for c in report.checks if c.status == "fail"]
        print(f"ARTEMIS IP Guardian: {report.status.upper()} "
              f"({len(report.checks)} checks, {len(failed)} failed)")
        for c in failed:
            print(f"  FAIL {c.check}: {c.target} — {c.detail}", file=sys.stderr)

    return 1 if (strict and report.status == "fail") else 0


if __name__ == "__main__":
    raise SystemExit(main())
