from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SafetyAndStructureTests(unittest.TestCase):
    def test_files_present(self):
        for name in ("index.html", "styles.css", "app.js", "README.md"):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_no_remote_endpoints_or_dynamic_execution(self):
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        for dangerous in (r"\bfetch\s*\(", r"\bWebSocket\s*\(", r"\bXMLHttpRequest\b", r"\beval\s*\(", r"\bnew\s+Function\s*\(", r"localStorage", r"sessionStorage"):
            self.assertIsNone(re.search(dangerous, js), dangerous)
        self.assertIn("state.halted", js)
        self.assertIn("gateDecisions", js)
        self.assertIn("append(", js)

    def test_no_external_dependency_in_html(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r'https?://')
        self.assertIn("SYNTHETIC ENVIRONMENT", html)
        self.assertIn("NO EXTERNAL ACTIONS", html)
        self.assertIn('id="stop-btn"', html)
        self.assertIn('id="approval-queue"', html)

    def test_reduced_motion_and_focus(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(":focus-visible", css)
        self.assertIn("max-width:800px", css)

if __name__ == "__main__":
    unittest.main()

