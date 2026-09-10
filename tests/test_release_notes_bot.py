# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/release_notes_bot.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.release_notes_bot import (  # noqa: E402
    COMMIT_TYPE_LABELS,
    SECTION_ORDER,
    CommitEntry,
    ReleaseNotes,
    _parse_commits,
    run,
)


class TestConstants:
    def test_section_order_includes_other(self) -> None:
        assert "Other" in SECTION_ORDER

    def test_every_label_is_in_section_order(self) -> None:
        for label in COMMIT_TYPE_LABELS.values():
            assert label in SECTION_ORDER


class TestParseCommits:
    def _log(self, lines: list[str]) -> str:
        return "\n".join(lines)

    def test_conventional_commit_parsing(self) -> None:
        log = self._log([
            "abc1234567|feat(ui): add button|Dev|2026-01-02 10:00:00 +0000",
            "def7654321|fix: correct typo|Dev|2026-01-01 09:00:00 +0000",
        ])
        with patch("bots.release_notes_bot._git", return_value=log):
            entries = _parse_commits("v1.0.0")
        assert len(entries) == 2
        assert entries[0].type == "feat"
        assert entries[0].scope == "ui"
        assert entries[0].sha == "abc1234"
        assert entries[1].type == "fix"

    def test_breaking_change_flag(self) -> None:
        log = self._log([
            "aaaaaaa1234|feat!: drop legacy API|Dev|2026-01-02 10:00:00 +0000",
        ])
        with patch("bots.release_notes_bot._git", return_value=log):
            entries = _parse_commits("v1.0.0")
        assert entries[0].breaking is True

    def test_non_conventional_falls_back_to_chore(self) -> None:
        log = self._log([
            "bbbbbbb1234|random commit message|Dev|2026-01-02 10:00:00 +0000",
        ])
        with patch("bots.release_notes_bot._git", return_value=log):
            entries = _parse_commits("v1.0.0")
        assert entries[0].type == "chore"
        assert entries[0].scope is None


class TestRun:
    def test_run_writes_outputs_and_orders_sections(self, tmp_path: Path) -> None:
        out = tmp_path / "output"
        log = "\n".join([
            "abc1234567|feat: new thing|Dev|2026-01-02 10:00:00 +0000",
            "def7654321|fix: a bug|Dev|2026-01-01 09:00:00 +0000",
        ])
        with patch("bots.release_notes_bot.OUTPUT_DIR", out), \
             patch("bots.release_notes_bot._get_last_tag", return_value="v1.0.0"), \
             patch("bots.release_notes_bot._git", return_value=log):
            notes = run()
        assert isinstance(notes, ReleaseNotes)
        assert notes.commit_count == 2
        assert (out / "release_notes.json").exists()
        assert (out / "release_notes.md").exists()
        # "New Features" must come before "Bug Fixes" per SECTION_ORDER
        keys = list(notes.sections.keys())
        assert keys.index("New Features") < keys.index("Bug Fixes")


class TestDataclasses:
    def test_commit_entry(self) -> None:
        c = CommitEntry(
            sha="abc1234", type="feat", scope=None,
            subject="x", author="Dev", date="2026-01-01", breaking=False,
        )
        assert c.breaking is False
