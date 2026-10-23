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
        self.assertEqual(len(self.products), 94)
        self.assertEqual([p["id"] for p in self.products[:82]], [f"cg-{i:03d}" for i in range(1, 83)])
        for key in ("id", "slug", "name", "description", "category", "status", "productUrl"):
            values = [product[key] for product in self.products]
            self.assertTrue(all(isinstance(value, str) and value for value in values), key)
            if key in {"id", "slug"}:
                self.assertEqual(len(values), len(set(values)), key)
        public_destinations = [
            product["productUrl"] for product in self.products
            if product.get("catalogVisibility") != "internal"
        ]
        self.assertEqual(len(public_destinations), len(set(public_destinations)), "public productUrl")

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

    def test_every_entry_has_evidence_metadata_and_a_safe_visibility_boundary(self) -> None:
        required = (
            "tagline", "audience", "keyCapabilities", "sourcePath", "publicUrl",
            "internalRoute", "repositoryPath", "documentationLink", "ctaLabel",
            "ctaDestination", "seoTitle", "seoDescription", "keywords",
            "last_verified", "evidence_notes", "integrationStatus", "catalogVisibility", "seoIndexable",
        )
        for product in self.products:
            for key in required:
                self.assertIn(key, product, f'{product["id"]}: {key}')
            for key in ("tagline", "audience", "sourcePath", "repositoryPath",
                        "ctaLabel", "ctaDestination", "seoTitle", "seoDescription",
                        "last_verified", "evidence_notes", "integrationStatus"):
                self.assertTrue(isinstance(product[key], str) and product[key], f'{product["id"]}: {key}')
            self.assertIsInstance(product["keyCapabilities"], list, product["id"])
            self.assertIsInstance(product["keywords"], list, product["id"])
            self.assertIsInstance(product["seoIndexable"], bool, product["id"])
            self.assertRegex(product["last_verified"], r"^\d{4}-\d{2}-\d{2}$")
            source = ROOT / product["sourcePath"]
            self.assertTrue(source.is_file(), f'{product["id"]} evidence source: {product["sourcePath"]}')
            if product["catalogVisibility"] == "internal":
                self.assertIsNone(product["publicUrl"], product["id"])
                self.assertFalse(product["seoIndexable"], product["id"])
                self.assertIsInstance(product["internalRoute"], str, product["id"])
                self.assertEqual(product["ctaLabel"], "Contact ClearGlass", product["id"])
                self.assertEqual(product["ctaDestination"], "/index.html#contact", product["id"])
            else:
                self.assertNotEqual(product["integrationStatus"], "INTERNAL / ADMIN", product["id"])
                self.assertIsInstance(product["publicUrl"], str, product["id"])
                self.assertTrue(product["publicUrl"].startswith("/"), product["id"])
                self.assertEqual(product["ctaDestination"], product["publicUrl"], product["id"])

    def test_structured_data_matches_public_catalog_entries(self) -> None:
        page = (ROOT / "products.html").read_text(encoding="utf-8")
        match = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', page)
        self.assertIsNotNone(match, "CollectionPage JSON-LD is required")
        schema = json.loads(match.group(1))
        self.assertEqual(schema["@type"], "CollectionPage")
        listed = schema["mainEntity"]["itemListElement"]
        expected_urls = {
            "https://www.clearglassinc.com" + product["publicUrl"]
            for product in self.products
            if product.get("catalogVisibility") != "internal"
            and isinstance(product.get("publicUrl"), str)
            and product["publicUrl"].startswith("/")
            and product.get("seoIndexable", True) is not False
        }
        actual_urls = {row["item"]["url"] for row in listed}
        self.assertEqual(actual_urls, expected_urls)
        self.assertEqual(schema["mainEntity"]["numberOfItems"], len(expected_urls))
        self.assertNotIn("complete verified", schema.get("description", "").lower())

    def test_internal_entries_do_not_link_their_implementation_routes_from_cards(self) -> None:
        page_script = (ROOT / "assets/js/product-command-center.js").read_text(encoding="utf-8")
        self.assertIn("productDestination(product)", page_script)
        self.assertIn("assessmentLabel(product)", page_script)
        for product in self.products:
            if product.get("catalogVisibility") == "internal":
                self.assertEqual(product["ctaDestination"], "/index.html#contact", product["id"])
                self.assertNotIn(product["internalRoute"], (product["ctaDestination"], product["publicUrl"]))

    def test_missing_navigation_catalog_entries_are_wired_without_removing_legacy_routes(self) -> None:
        nav = (ROOT / "nav.js").read_text(encoding="utf-8")
        self.assertIn('"XENOLITH", "xenolith.html"', nav)
        self.assertIn('"ARTEMIS FAWL", "artemis-fawl/index.html"', nav)
        self.assertIn('"Shield Concept Dashboard", "clearglass_x5f_shield_x5f_dashboard.html"', nav)
        self.assertIn('"GridShield-Ontario Evidence Console", "GridShield-Ontario-V6-0-ULTRA-FINAL.html"', nav)
        self.assertIn('["Authority Network", "authority-network.html", "Connected knowledge graph", "🔗"]', nav)
        self.assertNotIn('["Authority Grid", "authority-network.html", "⌁"]', nav)

    def test_noindex_routes_are_excluded_from_search_surfaces_without_deleting_pages(self) -> None:
        by_slug = {product["slug"]: product for product in self.products}
        platform = by_slug["platform-command-center"]
        self.assertEqual(platform["productUrl"], "/platform-command-center.html")
        self.assertEqual(platform["publicUrl"], "/platform-command-center.html")
        self.assertFalse(platform["seoIndexable"])
        self.assertTrue((ROOT / "platform-command-center.html").is_file())

        noindex_public = [
            product for product in self.products
            if product.get("publicUrl") and product.get("seoIndexable") is False
        ]
        self.assertGreaterEqual(len(noindex_public), 5)
        for product in noindex_public:
            page_path = ROOT / product["publicUrl"].lstrip("/")
            self.assertTrue(page_path.is_file(), f'{product["id"]}: {product["publicUrl"]}')
            page = page_path.read_text(encoding="utf-8")
            robots_tags = [
                tag.lower() for tag in re.findall(r"<meta[^>]*>", page, flags=re.IGNORECASE)
                if "robots" in tag.lower()
            ]
            self.assertTrue(
                any("noindex" in tag for tag in robots_tags),
                f'{product["id"]} is non-indexable but has no noindex robots directive',
            )

        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        for product in noindex_public:
            self.assertNotIn("https://www.clearglassinc.com" + product["publicUrl"], sitemap)
        page = (ROOT / "products.html").read_text(encoding="utf-8")
        match = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', page)
        self.assertIsNotNone(match)
        schema = json.loads(match.group(1))
        urls = {row["item"]["url"] for row in schema["mainEntity"]["itemListElement"]}
        for product in noindex_public:
            self.assertNotIn("https://www.clearglassinc.com" + product["publicUrl"], urls)

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
        self.assertEqual(set(expected) - set(by_slug), set())
        art = by_slug["artemis-fawl"]
        self.assertEqual(art["status"], "demo")
        self.assertEqual(art["integrationStatus"], "BETA / DEMO")
        self.assertEqual(art["productUrl"], "/artemis-fawl/index.html")
        self.assertIn("simulated", art["evidence_notes"].lower())
        for slug, (status, url) in expected.items():
            product = by_slug[slug]
            self.assertEqual(product["status"], status, slug)
            self.assertEqual(product["productUrl"], url, slug)
            self.assertNotIn("price", product, slug)
            self.assertNotIn("stripeProductId", product, slug)
            self.assertNotIn("stripePriceId", product, slug)


if __name__ == "__main__":
    unittest.main()
