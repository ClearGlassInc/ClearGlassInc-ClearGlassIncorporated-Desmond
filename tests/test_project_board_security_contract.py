# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Security regression contracts for the browser-only Project Board boundary."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from tools import project_board

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "project-board.js"


class ProjectBoardSecurityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.feed = project_board.load()

    def test_runtime_has_explicit_local_state_limits(self) -> None:
        for token in ("MAX_TASKS = 500", "MAX_SUBTASKS = 100",
                      "MAX_TITLE = 120", "MAX_SUBTASK_TITLE = 240"):
            self.assertIn(token, self.script)

    def test_runtime_validates_referential_integrity(self) -> None:
        for token in ("hasId(data.columns || [], task.column)",
                      "hasId(data.sprints || [], task.sprint)",
                      "hasId(data.members || [], aid)",
                      "validateLocalState(saved)"):
            self.assertIn(token, self.script)

    def test_runtime_rejects_invalid_local_state_instead_of_rendering_it(self) -> None:
        self.assertRegex(self.script, r"if \(!validateLocalState\(saved\)\)")
        self.assertIn('localStorage.removeItem(STORE)', self.script)

    def test_user_text_is_not_rendered_with_innerhtml(self) -> None:
        self.assertNotIn("innerHTML", self.script)

    def test_adversarial_titles_are_bounded(self) -> None:
        for title in ("<script>alert(1)</script>", "A" * 121, "\x00" * 121):
            self.assertFalse(
                isinstance(title, str) and len(title) <= 120 and title.strip() != ""
                and not re.search(r"[<>]", title),
                title,
            )

    def test_adversarial_dates_are_not_accepted_by_feed_contract(self) -> None:
        cases = ("2026-13-99", "not-a-date", "2026-12-24T12:00:00Z")
        for value in cases:
            broken = dict(self.feed)
            broken["tasks"] = [dict(self.feed["tasks"][0], start=value)]
            problems = project_board.validate(broken)
            self.assertTrue(problems, value)

    def test_adversarial_assignees_are_rejected_by_feed_contract(self) -> None:
        for assignee in ("ghost", "<script>", 123):
            broken = dict(self.feed)
            task = dict(self.feed["tasks"][0])
            task["assignees"] = list(task["assignees"]) + [assignee]
            broken["tasks"] = [task]
            problems = project_board.validate(broken)
            self.assertTrue(problems, repr(assignee))

    def test_adversarial_priorities_are_rejected_by_feed_contract(self) -> None:
        for priority in ("urgent", "", None):
            broken = dict(self.feed)
            task = dict(self.feed["tasks"][0], priority=priority)
            broken["tasks"] = [task]
            problems = project_board.validate(broken)
            self.assertTrue(problems, repr(priority))


if __name__ == "__main__":
    unittest.main()
