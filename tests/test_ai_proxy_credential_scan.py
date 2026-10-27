"""The secret scan in ai-proxy-security.yml must find keys, not English words.

Its OpenAI pattern was ``sk-[A-Za-z0-9_-]{20,}`` with no left boundary, so it
fired inside "ta·sk-…" and "ri·sk-…": a Copilot branch name in
operations/output/ci-audit/ and the NIST "ai-risk-management-framework" URL.
The secret-scan job failed on those from 2026-09-06, hidden by the runner lock.

The patterns are read from the workflow and run through ``grep -E`` exactly as
the job runs them. Key-shaped strings are assembled at runtime so this file
holds nothing the scan itself would flag.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ai-proxy-security.yml"

pytestmark = pytest.mark.skipif(shutil.which("grep") is None, reason="needs grep")


def scan_step() -> str:
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    return next(
        s["run"]
        for s in jobs["secret-scan"]["steps"]
        if s.get("name") == "Scan tracked files for credential material"
    )


def patterns() -> list[str]:
    block = re.search(r"patterns=\((.*?)\n\s*\)", scan_step(), re.S)
    assert block, "patterns=( ... ) not found in the secret-scan step"
    return re.findall(r"^\s*'([^']+)'\s*$", block.group(1), re.M)


def flagged(text: str) -> list[str]:
    hits = []
    for pattern in patterns():
        result = subprocess.run(
            ["grep", "-nEI", "-e", pattern], input=text, capture_output=True, text=True
        )
        if result.returncode == 0:
            hits.append(pattern)
    return hits


KEY_BODY = "Ab1" * 8  # 24 key-alphabet characters

BENIGN = [
    "head branch `copilot/ta" + "sk-" + "272290681-1196426665-" + "abc`",
    "https://www.nist.gov/itl/ai-ri" + "sk-" + "management-framework-and-profiles",
    "a d" + "isk-" + "encryption-at-rest-baseline-control",
]

KEYS = [
    "OPENAI_API_KEY=sk-" + KEY_BODY,
    '"apiKey": "sk-proj-' + KEY_BODY + '"',
    "Authorization: Bearer sk-" + KEY_BODY,
    "sk-" + KEY_BODY,
    "key: 'sk-" + KEY_BODY + "'",
]


def test_the_scan_still_has_its_patterns() -> None:
    assert len(patterns()) >= 6


@pytest.mark.parametrize("text", BENIGN)
def test_words_ending_in_sk_are_not_keys(text: str) -> None:
    assert flagged(text) == []


@pytest.mark.parametrize("text", KEYS)
def test_real_key_shapes_are_still_caught(text: str) -> None:
    assert flagged(text), f"no pattern matched {text[:24]}..."


def test_tracked_files_pass_the_scan() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("needs a git checkout")
    result = subprocess.run(
        ["bash", "-c", scan_step()], cwd=ROOT, capture_output=True, text=True, timeout=600
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-1000:]
