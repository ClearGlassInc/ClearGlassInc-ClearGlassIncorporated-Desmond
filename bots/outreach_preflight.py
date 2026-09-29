#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Outreach pre-send gate: refuse a commercial email that is not ready to send.

On 2026-09-29 follow-up emails went out with a template placeholder still in
the signature, on the line where the mailing address belonged. The drafts had
been prepared with the placeholder, and nothing stood between draft and Send.

This gate is that missing step. Run it on the exact text about to be sent (a
file per message, or stdin). It never sends anything and has no mail transport.

Hard failures (exit 1):
  PLACEHOLDER      an unfilled template token anywhere in the message
  MAILING_ADDRESS  no Canadian postal code in the new text. A city and province
                   alone ("Burlington, Ontario") is not a mailing address
  OPT_OUT          no unsubscribe / reply-STOP instruction in the new text
  SENDER_ID        "ClearGlass Inc." not named in the new text
  DEAD_CONTACT     a contact address on clearglassinc.com, which has no MX
                   record, so replies to it bounce (tests/test_contact_addresses.py)

Warnings (exit 0):
  HEALTH_SECTOR    the playbook flags health-sector recipients for human review
                   (offers/outreach/README.md)

"New text" is the message minus quoted reply lines (``>``) and everything after
an ``On ... wrote:`` line: a follow-up must carry its own identification and
opt-out, not lean on the quoted original.

Usage:
    python -m bots.outreach_preflight message.txt [more.txt ...]
    pbpaste | python -m bots.outreach_preflight -
    python -m bots.outreach_preflight --json message.txt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

PLACEHOLDER_RE = re.compile(
    r"\[(?:ADD|INSERT|FILL|REPLACE|TODO|TBD|YOUR|PLACEHOLDER)\b[^\]]*\]"
    r"|\{\{[^}]*\}\}"
    r"|<<[^>]*>>"
    r"|\bTODO\b|\bTBD\b|\bXXX\b|\bLorem ipsum\b",
    re.IGNORECASE,
)
# Canada Post letters: no D F I O Q U anywhere, and no W or Z in first position.
POSTAL_CODE_RE = re.compile(
    r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z][ -]?\d[ABCEGHJ-NPRSTV-Z]\d\b",
    re.IGNORECASE,
)
OPT_OUT_RE = re.compile(
    r"unsubscribe|opt[ -]?out|reply\s+\W?stop\b|\bstop\b\W*\s+(?:and|to)\b",
    re.IGNORECASE,
)
SENDER_RE = re.compile(r"ClearGlass\s+Inc\b", re.IGNORECASE)
DEAD_CONTACT_RE = re.compile(r"[A-Za-z0-9._%+-]+@clearglassinc\.com", re.IGNORECASE)
HEALTH_RE = re.compile(
    r"\b(?:patients?|clinics?|clinical|dental|dentist|medical|PHIPA|physio\w*|pharmac\w*)\b",
    re.IGNORECASE,
)
REPLY_HEADER_RE = re.compile(r"^On .+wrote:\s*$")


@dataclass
class Finding:
    code: str
    detail: str


@dataclass
class Result:
    source: str
    failures: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.failures


def new_text(message: str) -> str:
    """The part of ``message`` the sender wrote this time."""
    kept = []
    for line in message.splitlines():
        if REPLY_HEADER_RE.match(line.strip()):
            break
        if line.lstrip().startswith(">"):
            continue
        kept.append(line)
    return "\n".join(kept)


def check(message: str, source: str = "<message>") -> Result:
    result = Result(source)
    fresh = new_text(message)

    tokens = sorted({m.group(0) for m in PLACEHOLDER_RE.finditer(message)})
    if tokens:
        result.failures.append(
            Finding("PLACEHOLDER", "unfilled template text: " + ", ".join(tokens))
        )
    if not POSTAL_CODE_RE.search(fresh):
        result.failures.append(
            Finding(
                "MAILING_ADDRESS",
                "no mailing address with a postal code (CASL); "
                "a city and province alone is not sufficient",
            )
        )
    if not OPT_OUT_RE.search(fresh):
        result.failures.append(
            Finding("OPT_OUT", "no unsubscribe or reply-STOP instruction (CASL)")
        )
    if not SENDER_RE.search(fresh):
        result.failures.append(Finding("SENDER_ID", 'sender not identified as "ClearGlass Inc."'))
    dead = sorted({m.group(0) for m in DEAD_CONTACT_RE.finditer(fresh)})
    if dead:
        result.failures.append(
            Finding(
                "DEAD_CONTACT",
                "clearglassinc.com has no MX record, replies bounce: " + ", ".join(dead),
            )
        )
    health = sorted({m.group(0).lower() for m in HEALTH_RE.finditer(message)})
    if health:
        result.warnings.append(
            Finding(
                "HEALTH_SECTOR",
                "health-sector wording (" + ", ".join(health) + "); "
                "the playbook flags these recipients for human review",
            )
        )
    return result


def _read(path: str) -> tuple[str, str]:
    if path == "-":
        return "<stdin>", sys.stdin.read()
    return path, Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", help="message files, or - for stdin")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    results = [check(text, source) for source, text in map(_read, args.paths)]
    if args.json:
        print(json.dumps(
            [asdict(r) | {"ready": r.ready} for r in results], indent=2
        ))
    else:
        for r in results:
            print(f"{'READY  ' if r.ready else 'BLOCKED'}  {r.source}")
            for f in r.failures:
                print(f"  FAIL {f.code}: {f.detail}")
            for w in r.warnings:
                print(f"  WARN {w.code}: {w.detail}")
    return 0 if all(r.ready for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
