# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/cpa_partner_outreach_bot.py."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bots import cpa_partner_outreach_bot as bot


class CpaPartnerOutreachBotTests(unittest.TestCase):
    def test_run_has_three_templates(self) -> None:
        run = bot.build_run()
        self.assertEqual(len(run.templates), 3)
        keys = {t.key for t in run.templates}
        self.assertEqual(
            keys,
            {"value_first_linkedin", "revenue_angle_email", "pilot_focused"},
        )

    def test_templates_carry_personalization_tokens(self) -> None:
        run = bot.build_run()
        for t in run.templates:
            self.assertIn("{{first_name}}", t.body, f"missing first_name in {t.key}")
            self.assertIn("{{sender_name}}", t.body, f"missing sender_name in {t.key}")

    def test_compliance_positioning_present_everywhere(self) -> None:
        run = bot.build_run()
        md = bot.build_markdown(run)
        # Legal AI must be framed as assistive, never legal advice.
        self.assertIn("assistive", md.lower())
        self.assertIn("PIPEDA", md)
        self.assertIn("no screen scraping", md.lower())
        self.assertEqual(len(run.compliance_notes), 4)

    def test_one_pager_has_partner_tiers(self) -> None:
        run = bot.build_run()
        tiers = {t.tier for t in run.one_pager.partner_tiers}
        self.assertEqual(tiers, {"Starter", "Growth", "White-label"})

    def test_execution_plan_covers_the_week(self) -> None:
        run = bot.build_run()
        self.assertEqual(len(run.execution_plan), 3)
        for step in run.execution_plan:
            self.assertTrue(step.actions, f"no actions for {step.days}")

    def test_markdown_renders_all_sections(self) -> None:
        run = bot.build_run()
        md = bot.build_markdown(run)
        self.assertIn("Outreach Templates", md)
        self.assertIn("CPA Partner One-Pager", md)
        self.assertIn("Weekly Micro Execution Plan", md)
        self.assertIn("Revenue Model", md)
        self.assertIn("KPI Targets", md)

    def test_write_outputs_creates_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run = bot.build_run()
            md_path, json_path = bot.write_outputs(run, output_dir=out)
            self.assertTrue(md_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue((out / "latest.md").exists())
            self.assertTrue((out / "latest.json").exists())
            data = json.loads((out / "latest.json").read_text())
            self.assertEqual(data["program"], "ClearGlass CPA Partner Program")
            self.assertEqual(len(data["templates"]), 3)


if __name__ == "__main__":
    unittest.main()
