"""Published contact addresses must be deliverable.

clearglassinc.com publishes no MX record (checked 2026-09-29 through the system
resolver: MX NoAnswer on the apex and on www; the A records are GitHub Pages,
which accepts no mail). Mail to any @clearglassinc.com address bounces back to
the sender and ClearGlass never sees it, so a contact link on that domain loses
the lead silently. Once the domain has a working MX, set DOMAIN_ACCEPTS_MAIL to
True and this guard stands down.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

DOMAIN_ACCEPTS_MAIL = False

# In pages: mailto: links, and compose deep links such as Outlook's
# `?to=name%40domain`. Form placeholders such as `you@clearglassinc.com` are not
# contact paths, so bare addresses in HTML are left alone.
DEAD_LINK = re.compile(
    r"(?:mailto:|to=)[A-Za-z0-9._%+-]+(?:@|%40)clearglassinc\.com", re.IGNORECASE
)
# In the policy files every address is a contact path.
DEAD_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@clearglassinc\.com", re.IGNORECASE)
SKIP_DIRS = {".git", "node_modules", "archive"}
POLICY_FILES = (
    "security.txt",
    ".well-known/security.txt",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    ".github/ISSUE_TEMPLATE/config.yml",
)


def published_pages() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.html")
        if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts)
    ]


def test_no_contact_link_points_at_a_domain_without_mx() -> None:
    if DOMAIN_ACCEPTS_MAIL:
        pytest.skip("clearglassinc.com accepts mail")
    scans = [(path, DEAD_LINK) for path in published_pages()] + [
        (ROOT / name, DEAD_ADDRESS) for name in POLICY_FILES
    ]
    offenders = [
        f"{path.relative_to(ROOT)}: {match.group(0)}"
        for path, pattern in scans
        for match in pattern.finditer(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert not offenders, (
        "undeliverable contact address (clearglassinc.com has no MX):\n" + "\n".join(offenders)
    )


def test_security_txt_copies_match() -> None:
    root_copy = (ROOT / "security.txt").read_text(encoding="utf-8")
    assert root_copy == (ROOT / ".well-known" / "security.txt").read_text(encoding="utf-8")
