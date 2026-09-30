"""Named-prospect outreach files must not be tracked.

The site ships with .nojekyll, so GitHub Pages publishes every tracked file.
Until 2026-09-30 the working lead list (ten named local firms, with notes such
as "likely no formal security review") and the personalised drafts built from
it were served on the company domain to the same firms being called and
emailed. Lead lists and generated drafts stay on the operator's machine
(.gitignore) and the live pipeline is kept in a private sheet. The empty
template stays tracked.
"""

from __future__ import annotations

import fnmatch
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

ALLOWED = {"offers/outreach/lead-list-template.csv"}
FORBIDDEN = (
    "offers/outreach/lead-list-*.csv",
    "offers/outreach/generated/*",
    "offers/outreach/drafts-*.md",
)


def tracked_files() -> list[str]:
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("needs a git checkout")
    out = subprocess.run(
        ["git", "ls-files", "offers/outreach"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.split()


def test_no_named_prospect_file_is_tracked():
    leaked = [
        path
        for path in tracked_files()
        if path not in ALLOWED
        and any(fnmatch.fnmatch(path, pattern) for pattern in FORBIDDEN)
    ]
    assert not leaked, (
        "These would be published on the company domain; keep them local "
        f"and log the pipeline in the private sheet: {leaked}"
    )


def test_template_is_still_tracked():
    assert "offers/outreach/lead-list-template.csv" in tracked_files()
