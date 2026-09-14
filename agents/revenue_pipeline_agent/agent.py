#!/usr/bin/env python3
"""Evidence-first commercial pipeline agent for ClearGlass.

This agent reports and validates pipeline state. It does not claim that
research, drafts, or automation are sales outcomes. External sending is not
implemented here; sending must occur through an explicitly approved channel.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROSPECTING = ROOT / "commercial" / "PROSPECTING_2026-09-13.md"

METRICS = {
    "Prospects researched": r"\| Prospects researched \|\s*(\d+)\s*\|",
    "Contacted": r"\| Contacted \|\s*(\d+)\s*\|",
    "Meetings": r"\| Meetings \|\s*(\d+)\s*\|",
    "Proposals": r"\| Proposals \|\s*(\d+)\s*\|",
    "Customers": r"\| Customers \|\s*(\d+)\s*\|",
    "Verified revenue": r"\| Verified revenue \|\s*([^|]+?)\s*\|",
    "Verified MRR": r"\| Verified MRR \|\s*([^|]+?)\s*\|",
}


def load() -> str:
    if not PROSPECTING.exists():
        raise SystemExit(f"NOT VERIFIED: missing {PROSPECTING}")
    return PROSPECTING.read_text(encoding="utf-8")


def report(text: str) -> int:
    print("CLEARGLASS REVENUE PIPELINE AGENT")
    print("=================================")
    for label, pattern in METRICS.items():
        match = re.search(pattern, text)
        value = match.group(1).strip() if match else "NOT VERIFIED"
        print(f"{label}: {value}")
    print("\nState machine: RESEARCHED -> CONTACTED -> RESPONDED -> MEETING -> PROPOSAL -> CUSTOMER -> REVENUE -> MRR")
    print("Evidence policy: unknown values remain NOT VERIFIED.")
    return 0


def validate(text: str) -> int:
    failures = []
    required_sections = ["## Live scoreboard", "## Contact evidence", "## Evidence rule"]
    for section in required_sections:
        if section not in text:
            failures.append(f"missing section: {section}")

    contacted_match = re.search(METRICS["Contacted"], text)
    contacted = int(contacted_match.group(1)) if contacted_match else None
    evidence_count = len(
        re.findall(r"^\s*(?:-\s*)?Message sent:\s*", text, flags=re.MULTILINE)
    )

    if contacted is None:
        failures.append("contacted metric is not verifiable")
    elif contacted != evidence_count:
        failures.append(f"Contacted={contacted} but message evidence records={evidence_count}")

    for forbidden in ["guaranteed customer", "guaranteed revenue", "guaranteed meeting"]:
        if forbidden.lower() in text.lower():
            failures.append(f"unsupported claim detected: {forbidden}")

    if failures:
        print("VALIDATION: FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("VALIDATION: PASS")
    print(f"Verified contact evidence records: {evidence_count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    text = load()

    if args.validate:
        return validate(text)
    return report(text)


if __name__ == "__main__":
    raise SystemExit(main())
