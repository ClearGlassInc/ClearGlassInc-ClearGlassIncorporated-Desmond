# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Release notes bot — generates structured release notes from git history."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "output"

# Maps conventional commit type → readable section heading
COMMIT_TYPE_LABELS: dict[str, str] = {
    "feat": "New Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "docs": "Documentation",
    "test": "Tests",
    "ci": "CI/CD",
    "chore": "Maintenance",
    "bot": "Automation",
    "security": "Security",
    "style": "Style",
    "build": "Build",
}

SECTION_ORDER = list(COMMIT_TYPE_LABELS.values()) + ["Other"]


@dataclass
class CommitEntry:
    sha: str
    type: str
    scope: str | None
    subject: str
    author: str
    date: str
    breaking: bool


@dataclass
class ReleaseNotes:
    run_utc: str
    from_tag: str | None
    to_ref: str
    commit_count: int
    sections: dict[str, list[dict[str, Any]]]
    breaking_changes: list[dict[str, Any]]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip()


def _get_last_tag() -> str | None:
    tag = _git("describe", "--tags", "--abbrev=0")
    return tag or None


def _parse_commits(from_ref: str | None, max_commits: int = 100) -> list[CommitEntry]:
    log_range = f"{from_ref}..HEAD" if from_ref else f"HEAD~{max_commits}..HEAD"
    raw = _git("log", log_range, "--pretty=format:%H|%s|%an|%ai", "--no-merges")

    entries: list[CommitEntry] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        sha, subject, author, date = parts

        m = re.match(
            r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$",
            subject,
        )
        if m:
            ctype = m.group("type").lower()
            scope = m.group("scope")
            breaking = bool(m.group("breaking"))
            subj = m.group("subject")
        else:
            ctype = "chore"
            scope = None
            breaking = False
            subj = subject

        entries.append(CommitEntry(
            sha=sha[:7], type=ctype, scope=scope,
            subject=subj, author=author, date=date[:10], breaking=breaking,
        ))

    return entries


def run() -> ReleaseNotes:
    last_tag = _get_last_tag()
    commits = _parse_commits(last_tag)

    sections: dict[str, list[dict[str, Any]]] = {}
    breaking: list[dict[str, Any]] = []

    for c in commits:
        label = COMMIT_TYPE_LABELS.get(c.type, "Other")
        sections.setdefault(label, []).append(asdict(c))
        if c.breaking:
            breaking.append(asdict(c))

    sorted_sections = {k: sections[k] for k in SECTION_ORDER if k in sections}

    notes = ReleaseNotes(
        run_utc=datetime.now(timezone.utc).isoformat(),
        from_tag=last_tag,
        to_ref="HEAD",
        commit_count=len(commits),
        sections=sorted_sections,
        breaking_changes=breaking,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "release_notes.json").write_text(json.dumps(asdict(notes), indent=2))

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md: list[str] = [
        f"# Release Notes — {date_str}",
        "",
        f"*{len(commits)} commit(s) since {last_tag or 'repository start'}*",
        "",
    ]

    if breaking:
        md += ["## ⚠️ Breaking Changes", ""]
        for c in breaking:
            scope_str = f"**{c['scope']}:** " if c["scope"] else ""
            md.append(f"- {scope_str}{c['subject']} (`{c['sha']}`)")
        md.append("")

    for section, entries in sorted_sections.items():
        md += [f"## {section}", ""]
        for c in entries:
            scope_str = f"**{c['scope']}:** " if c["scope"] else ""
            md.append(f"- {scope_str}{c['subject']} (`{c['sha']}`)")
        md.append("")

    (OUTPUT_DIR / "release_notes.md").write_text("\n".join(md))
    return notes


def main() -> None:
    notes = run()
    print(f"Release notes: {notes.commit_count} commit(s) since {notes.from_tag or 'start'}")
    if notes.breaking_changes:
        print(f"⚠️  {len(notes.breaking_changes)} breaking change(s)")


if __name__ == "__main__":
    main()
