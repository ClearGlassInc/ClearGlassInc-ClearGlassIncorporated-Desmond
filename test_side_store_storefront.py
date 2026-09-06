# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Validates the ClearGlass Side Store storefront seed catalog and runs the
JavaScript pricing/checkout smoke test through the repo's pytest CI so the
storefront core is exercised on every build (Node is present on CI runners)."""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOREFRONT = ROOT / "apps" / "autostore" / "storefront"
CATALOG = STOREFRONT / "data" / "catalog.json"
NODE_TEST = STOREFRONT / "lib" / "store.test.mjs"


class CatalogInvariantsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.items = self.data["items"]

    def test_has_at_least_50_skus(self) -> None:
        self.assertGreaterEqual(len(self.items), 50)

    def test_currency_is_cad(self) -> None:
        self.assertEqual(self.data["currency"], "CAD")

    def test_ids_and_skus_are_unique(self) -> None:
        ids = [it["id"] for it in self.items]
        skus = [it["sku"] for it in self.items]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids")
        self.assertEqual(len(skus), len(set(skus)), "duplicate skus")

    def test_every_item_is_cheap_and_well_formed(self) -> None:
        for it in self.items:
            for field in ("id", "sku", "name", "category", "price", "currency"):
                self.assertIn(field, it, f"{it.get('sku')}: missing {field}")
            self.assertEqual(it["currency"], "CAD")
            self.assertGreater(it["price"], 0)
            self.assertLessEqual(it["price"], 10, f"{it['sku']} exceeds $10 impulse cap")


class PricingSmokeTest(unittest.TestCase):
    def test_node_pricing_suite_passes(self) -> None:
        node = shutil.which("node")
        if node is None:  # pragma: no cover - CI always has node
            self.skipTest("node not available")
        result = subprocess.run(
            [node, "--test", str(NODE_TEST)],
            capture_output=True, text=True, cwd=str(ROOT), timeout=120,
        )
        self.assertEqual(result.returncode, 0,
                         f"node smoke test failed:\n{result.stdout}\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
