# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Contract tests for the ClearGlass Project Board console.

``project-board.html`` ships an empty shell: every column, card, time-sheet row,
gauge segment, activity item and calendar slot is rendered by ``project-board.js``
from ``data/project-board/board.json``. There is deliberately no inline copy of the
data to fall back on, so a dangling reference in the feed is a blank region on
the page. These tests pin the feed's referential integrity, the page's wiring to
its assets, and the handful of rendering invariants the stylesheet depends on.
"""
from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

from tools import project_board

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "data" / "project-board" / "board.json"
PAGE = ROOT / "project-board.html"
SCRIPT = ROOT / "project-board.js"
STYLES = ROOT / "project-board.css"


class FeedIntegrityTests(unittest.TestCase):
    """The shipped feed must pass its own validator with nothing outstanding."""

    def setUp(self) -> None:
        self.feed = project_board.load()

    def test_shipped_feed_validates(self) -> None:
        self.assertEqual(project_board.validate(self.feed), [])

    def test_page_is_wired_to_feed_and_assets(self) -> None:
        self.assertEqual(project_board.validate_wiring(), [])

    def test_schema_is_pinned(self) -> None:
        self.assertEqual(self.feed["schema"], project_board.SCHEMA)

    def test_board_has_every_column_the_design_calls_for(self) -> None:
        ids = [c["id"] for c in self.feed["columns"]]
        self.assertEqual(
            ids,
            ["in-progress", "ready-for-sprint", "dev-qa",
             "ready-to-design", "final-review", "completed"],
        )

    def test_two_columns_start_collapsed_as_vertical_rails(self) -> None:
        collapsed = [c["id"] for c in self.feed["columns"] if c.get("collapsed")]
        self.assertEqual(collapsed, ["ready-for-sprint", "dev-qa"])

    def test_every_open_column_has_cards_to_render(self) -> None:
        counts = project_board.summarise(self.feed)["by_column"]
        for column in self.feed["columns"]:
            self.assertGreater(
                counts[column["id"]], 0,
                f"column {column['id']} would render empty",
            )

    def test_exactly_one_timesheet_entry_is_running(self) -> None:
        # The live ticker increments running entries once a second; two runners
        # would let the leaderboard reorder under the user's pointer.
        running = [e for e in self.feed["timesheet"]["entries"] if e.get("running")]
        self.assertEqual(len(running), 1)

    def test_running_entry_leads_the_timesheet(self) -> None:
        entries = self.feed["timesheet"]["entries"]
        leader = max(entries, key=lambda e: e["seconds"])
        self.assertTrue(leader.get("running"), "the leader row is the one that ticks")

    def test_activity_default_range_matches_the_designed_view(self) -> None:
        # The widget opens on "Today" (<= 24h). Three items is what the layout
        # is drawn for; the older ones exist so the range selector does something.
        today = [a for a in self.feed["activity"] if a["hours"] <= 24]
        self.assertEqual(len(today), 3)
        self.assertLess(len(today), len(self.feed["activity"]))

    def test_exactly_one_upload_is_still_in_flight(self) -> None:
        in_flight = [a for a in self.feed["activity"]
                     if a.get("file") and a["file"]["percent"] < 100]
        self.assertEqual(len(in_flight), 1)

    def test_selected_day_has_a_schedule(self) -> None:
        selected = self.feed["calendar"]["selected"]
        slots = [s for s in self.feed["calendar"]["schedule"] if s["date"] == selected]
        self.assertGreater(len(slots), 0)

    def test_every_week_day_has_at_least_one_slot(self) -> None:
        dated = {s["date"] for s in self.feed["calendar"]["schedule"]}
        for day in self.feed["calendar"]["days"]:
            self.assertIn(day["date"], dated, f"{day['date']} would render empty")

    def test_feed_is_committed_as_formatted_json(self) -> None:
        raw = FEED.read_text(encoding="utf-8")
        self.assertEqual(raw, json.dumps(self.feed, indent=2, ensure_ascii=False) + "\n")


class ValidatorTests(unittest.TestCase):
    """The validator has to actually catch the breakages it claims to."""

    def setUp(self) -> None:
        self.feed = project_board.load()

    def _broken(self, mutate) -> list[str]:
        feed = copy.deepcopy(self.feed)
        mutate(feed)
        return project_board.validate(feed)

    def test_unknown_column_is_caught(self) -> None:
        problems = self._broken(lambda f: f["tasks"][0].update(column="nowhere"))
        self.assertTrue(any("unknown column" in p for p in problems), problems)

    def test_unknown_board_is_caught(self) -> None:
        problems = self._broken(lambda f: f["tasks"][0].update(board="nowhere"))
        self.assertTrue(any("unknown board" in p for p in problems), problems)

    def test_unknown_sprint_is_caught(self) -> None:
        problems = self._broken(lambda f: f["tasks"][0].update(sprint="sprint-99"))
        self.assertTrue(any("unknown sprint" in p for p in problems), problems)

    def test_unknown_assignee_is_caught(self) -> None:
        problems = self._broken(lambda f: f["tasks"][0]["assignees"].append("ghost"))
        self.assertTrue(any("unknown assignee" in p for p in problems), problems)

    def test_backwards_date_range_is_caught(self) -> None:
        def mutate(feed: dict) -> None:
            feed["tasks"][0]["start"] = "2026-12-24"
            feed["tasks"][0]["end"] = "2026-12-19"
        problems = self._broken(mutate)
        self.assertTrue(any("before it starts" in p for p in problems), problems)

    def test_unknown_priority_is_caught(self) -> None:
        problems = self._broken(lambda f: f["tasks"][0].update(priority="urgent"))
        self.assertTrue(any("priority" in p for p in problems), problems)

    def test_duplicate_task_id_is_caught(self) -> None:
        def mutate(feed: dict) -> None:
            feed["tasks"].append(copy.deepcopy(feed["tasks"][0]))
        problems = self._broken(mutate)
        self.assertTrue(any("duplicate ids" in p for p in problems), problems)

    def test_child_board_shadowing_a_parent_is_caught(self) -> None:
        def mutate(feed: dict) -> None:
            feed["boards"][1]["children"][0]["id"] = feed["boards"][0]["id"]
        problems = self._broken(mutate)
        self.assertTrue(any("boards: duplicate ids" in p for p in problems), problems)

    def test_schedule_slot_off_the_week_strip_is_caught(self) -> None:
        problems = self._broken(lambda f: f["calendar"]["schedule"][0].update(date="2027-06-01"))
        self.assertTrue(any("off the week strip" in p for p in problems), problems)

    def test_velocity_percent_out_of_range_is_caught(self) -> None:
        problems = self._broken(lambda f: f["velocity"]["series"][0].update(percent=140))
        self.assertTrue(any("outside 0-100" in p for p in problems), problems)

    def test_selected_velocity_series_must_exist(self) -> None:
        problems = self._broken(lambda f: f["velocity"].update(selected="Dec"))
        self.assertTrue(any("is not one of" in p for p in problems), problems)

    def test_missing_top_level_key_is_caught(self) -> None:
        problems = self._broken(lambda f: f.pop("calendar"))
        self.assertTrue(any("missing top-level key" in p for p in problems), problems)

    def test_wrong_schema_is_caught(self) -> None:
        problems = self._broken(lambda f: f.update(schema="something/v9"))
        self.assertTrue(any("schema is" in p for p in problems), problems)


class PageContractTests(unittest.TestCase):
    """What the renderer needs from the markup, and the markup from the feed."""

    def setUp(self) -> None:
        self.page = PAGE.read_text(encoding="utf-8")
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.styles = STYLES.read_text(encoding="utf-8")

    def test_every_mount_point_the_script_renders_into_exists(self) -> None:
        mounts = [
            "pb-board", "pb-projects", "pb-tree", "pb-sprints", "pb-sheet",
            "pb-gauge", "pb-legend", "pb-feed", "pb-week", "pb-sched",
            "pb-scope", "pb-toast", "pb-dialog", "pb-form",
        ]
        for mount in mounts:
            self.assertIn(f'id="{mount}"', self.page, f"missing mount point #{mount}")

    def test_every_icon_the_script_uses_is_defined_in_the_sprite(self) -> None:
        defined = set(re.findall(r'<symbol id="(i-[a-z-]+)"', self.page))
        used = set(re.findall(r'icon\("(i-[a-z-]+)"', self.script))
        used |= set(re.findall(r'href="#(i-[a-z-]+)"', self.page))
        # The project glyphs are looked up by name from the feed, not literally.
        feed = project_board.load()
        used |= {"i-" + p["glyph"] for p in feed["projects"]}
        self.assertEqual(used - defined, set(), "icons referenced but never defined")

    def test_page_has_exactly_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1\b", self.page)), 1)

    def test_page_carries_canonical_title_and_description(self) -> None:
        self.assertIn('rel="canonical"', self.page)
        self.assertRegex(self.page, r"<title>[^<]{20,70}</title>")
        self.assertRegex(self.page, r'name="description" content="[^"]{80,165}"')

    def test_structured_data_parses(self) -> None:
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', self.page, re.S
        )
        self.assertTrue(blocks)
        for block in blocks:
            json.loads(block)

    def test_full_viewport_shell_hides_body_overflow(self) -> None:
        # The internal-link generator keys its fixed corner chip off this, so the
        # page is registered in tools/internal_links.py's FIXED_VIEWPORT set.
        self.assertRegex(self.styles, r"body\.pb-body\s*\{[^}]*overflow:\s*hidden")

    def test_light_theme_repaints_every_surface_token(self) -> None:
        dark = set(re.findall(r"(--[a-z0-9-]+):", self._block(self.styles, ":root {")))
        light = set(re.findall(r"(--[a-z0-9-]+):", self._block(self.styles, '[data-theme="light"] {')))
        surfaces = {"--bg", "--bg-2", "--surface", "--card", "--card-2", "--card-3",
                    "--line", "--line-2", "--line-3", "--ink", "--ink-2", "--ink-3"}
        self.assertTrue(surfaces <= dark)
        self.assertTrue(surfaces <= light, f"light theme leaves {sorted(surfaces - light)} dark")

    @staticmethod
    def _block(text: str, opener: str) -> str:
        start = text.index(opener) + len(opener)
        return text[start:text.index("}", start)]

    def test_script_never_writes_feed_text_through_innerhtml(self) -> None:
        # Task titles and comment bodies are user input by the time they round-trip
        # through localStorage; the renderer builds nodes and sets textContent.
        self.assertNotIn("innerHTML", self.script)


if __name__ == "__main__":
    unittest.main()
