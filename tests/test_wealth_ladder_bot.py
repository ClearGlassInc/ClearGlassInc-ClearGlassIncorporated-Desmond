# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from bots import wealth_ladder_bot as wl


class WealthLadderTests(unittest.TestCase):
    def test_empty_ledger_focuses_on_revenue(self) -> None:
        plan = wl.build_plan(wl.Ledger())
        self.assertEqual(plan.focus_key, "revenue")
        self.assertEqual(plan.rungs[0].key, "revenue")
        self.assertFalse(plan.rungs[0].satisfied)

    def test_trust_is_gated_behind_assets(self) -> None:
        # Everything done EXCEPT assets are below the floor — trust must lock.
        ledger = wl.Ledger(
            monthly_revenue=Decimal("9000"),
            incorporated=True,
            business_credit_score=90,
            investable_assets=Decimal("5000"),
            trust_established=True,
        )
        rungs = {r.key: r for r in wl.evaluate_ladder(ledger)}
        self.assertTrue(rungs["trust"].locked)
        self.assertFalse(rungs["trust"].satisfied)
        self.assertEqual(rungs["trust"].rationale, wl.THESIS)

    def test_trust_unlocks_once_assets_clear_floor(self) -> None:
        ledger = wl.Ledger(
            monthly_revenue=Decimal("9000"),
            incorporated=True,
            business_credit_score=90,
            investable_assets=Decimal("150000"),
            trust_established=True,
        )
        rungs = {r.key: r for r in wl.evaluate_ladder(ledger)}
        self.assertFalse(rungs["trust"].locked)
        self.assertTrue(rungs["trust"].satisfied)

    def test_focus_advances_when_revenue_met(self) -> None:
        ledger = wl.Ledger(monthly_revenue=Decimal("6000"), revenue_target=Decimal("5000"))
        plan = wl.build_plan(ledger)
        # Revenue satisfied → focus moves to the next unlocked rung (corporation).
        self.assertEqual(plan.focus_key, "corporation")

    def test_locked_rungs_below_unmet_prerequisite(self) -> None:
        # No revenue → corporation and everything above should be locked.
        rungs = {r.key: r for r in wl.evaluate_ladder(wl.Ledger())}
        self.assertTrue(rungs["corporation"].locked)
        self.assertTrue(rungs["business_credit"].locked)

    def test_markdown_carries_thesis_and_services(self) -> None:
        plan = wl.build_plan(wl.Ledger())
        md = wl.build_markdown(plan)
        self.assertIn(wl.THESIS, md)
        self.assertIn("AI risk assessments", md)
        self.assertIn("Canada Disability Benefit", md)
        self.assertIn("FASTEST LEGAL WAY TO GET PAID NOW", md)

    def test_ledger_from_dict_override(self) -> None:
        ledger = wl.Ledger.from_dict({"monthly_revenue": "7500", "incorporated": True})
        self.assertEqual(ledger.monthly_revenue, Decimal("7500"))
        self.assertTrue(ledger.incorporated)

    def test_load_ledger_merges_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            path.write_text(json.dumps({"monthly_revenue": "12000"}), encoding="utf-8")
            ledger = wl.load_ledger(path)
            self.assertEqual(ledger.monthly_revenue, Decimal("12000"))

    def test_write_outputs_creates_latest_and_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "wealth_ladder"
            archive_dir = output_dir / "archive"
            orig_out, orig_arch = wl.OUTPUT_DIR, wl.ARCHIVE_DIR
            try:
                wl.OUTPUT_DIR, wl.ARCHIVE_DIR = output_dir, archive_dir
                plan = wl.build_plan(wl.Ledger())
                wl.write_outputs(plan)
                self.assertTrue((output_dir / "latest.md").exists())
                payload = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["rungs"][0]["key"], "revenue")
                self.assertGreater(len(list(archive_dir.glob("*.json"))), 0)
            finally:
                wl.OUTPUT_DIR, wl.ARCHIVE_DIR = orig_out, orig_arch


if __name__ == "__main__":
    unittest.main()
