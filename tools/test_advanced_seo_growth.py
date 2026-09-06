#!/usr/bin/env python3
"""Deterministic regression tests for the Advanced SEO Growth engine."""
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("advanced_seo_growth.py")
spec = importlib.util.spec_from_file_location("advanced_seo_growth", MODULE_PATH)
seo = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(seo)


class ParserTests(unittest.TestCase):
    def parse(self, html: str):
        parser = seo.PageParser()
        parser.feed(html)
        return parser

    def test_non_visible_code_is_not_counted(self):
        parser = self.parse("<style>hidden style words</style><script>hidden script words</script><p>Visible content only</p>")
        self.assertEqual(" ".join(parser.text), "Visible content only")

    def test_json_ld_is_preserved_but_not_visible_text(self):
        parser = self.parse('<script type="application/ld+json">{"@type":"Article"}</script><p>Body</p>')
        self.assertEqual(parser.schema, ['{"@type":"Article"}'])
        self.assertEqual(parser.text, ["Body"])

    def test_relative_link_normalization(self):
        self.assertEqual(seo.normalize_internal("../about", "blog/post.html"), "about.html")
        self.assertEqual(seo.normalize_internal("/legal/", "index.html"), "legal/index.html")

    def test_external_and_non_http_links_are_ignored(self):
        self.assertIsNone(seo.normalize_internal("https://example.com/x", "index.html"))
        self.assertIsNone(seo.normalize_internal("mailto:test@example.com", "index.html"))

    def test_ci_execution_sentinel(self):
        """Sentinel changed only to force and verify the pull-request workflow path."""
        self.assertEqual(seo.SITE, "https://www.clearglassinc.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
