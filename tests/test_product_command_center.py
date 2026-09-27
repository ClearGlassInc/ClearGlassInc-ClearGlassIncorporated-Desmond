import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


class ProductCommandCenterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads((ROOT / "data/products.json").read_text())
        cls.products = cls.catalog["products"]

    def test_catalog_has_unique_required_identifiers(self) -> None:
        self.assertEqual(self.catalog["schema"], "clearglass.products/v1")
        self.assertEqual(len(self.products), 82)
        for key in ("id", "slug", "name", "description", "category", "status", "productUrl"):
            values = [product[key] for product in self.products]
            self.assertTrue(all(isinstance(value, str) and value for value in values), key)
            if key in {"id", "slug", "productUrl"}:
                self.assertEqual(len(values), len(set(values)), key)

    def test_every_internal_product_destination_exists(self) -> None:
        for product in self.products:
            parsed = urlparse(product["productUrl"])
            if parsed.scheme or not parsed.path.startswith("/"):
                continue
            relative = parsed.path.lstrip("/") or "index.html"
            destination = ROOT / relative
            if destination.suffix == "":
                destination = destination.with_suffix(".html")
            self.assertTrue(destination.is_file(), f'{product["name"]}: {parsed.path}')

    def test_page_loads_authoritative_catalog_and_command_script(self) -> None:
        page = (ROOT / "products.html").read_text()
        self.assertIn('data-catalog-url="/data/products.json"', page)
        self.assertIn('/assets/js/product-command-center.js', page)
        self.assertIn('/assets/css/product-command-center.css', page)
        self.assertEqual(len(re.findall(r'data-product-command-center(?:\s|>)', page)), 1)

    def test_new_product_surfaces_are_explicitly_noncommercial(self) -> None:
        expected = {
            "revenue-machine": ("internal", "/ClearGlass-Revenue-Machine.html"),
            "revenue-os-v2": ("internal", "/clearGlass-revenue-os-v2.html"),
            "clearglass-shield": ("architecture-stage", "/shield.html"),
            "shield-g01-verification-console": ("simulation", "/clearglass_x5f_shield_x5f_g01_x5f_verified.html"),
            "shield-nexus-simulation": ("simulation", "/shield_x5f_nexus_x5f_live_x5f_all.html"),
            "gridshield-ontario-ultra": ("simulation", "/gridshield_x5f_v6_x5f_ultra_x5f_do.html"),
            "ontario-power-grid-live-demo": ("demo", "/ontario_x5f_power_x5f_grid_x5f_live.html"),
        }
        by_slug = {product["slug"]: product for product in self.products}
        self.assertEqual(set(expected), set(by_slug))
        for slug, (status, url) in expected.items():
            product = by_slug[slug]
            self.assertEqual(product["status"], status, slug)
            self.assertEqual(product["productUrl"], url, slug)
            self.assertNotIn("price", product, slug)
            self.assertNotIn("stripeProductId", product, slug)
            self.assertNotIn("stripePriceId", product, slug)


if __name__ == "__main__":
    unittest.main()
