import json
import tempfile
import unittest
from pathlib import Path

from bots import priority_matrix_bot


class PriorityMatrixBotTests(unittest.TestCase):
    def test_build_markdown_contains_matrix(self) -> None:
        brief = priority_matrix_bot.build_brief()
        md = priority_matrix_bot.build_markdown(brief)
        self.assertIn("PRIORITY MATRIX", md)
        self.assertIn("| P0 | AI Automation | Finish core workflow script |", md)
        self.assertIn("| P1 | Cybersecurity | Audit ClearGlassInc endpoint |", md)
        self.assertIn("| P2 | Personal Brand | 1 LinkedIn post |", md)

    def test_brief_carries_owner_mantra_and_review(self) -> None:
        brief = priority_matrix_bot.build_brief()
        self.assertEqual(brief.mantra, "I own this day. My P0 tasks get done. Let's execute.")
        self.assertEqual(brief.yesterday_review, "Report your 3 pledges + completion.")
        self.assertEqual(brief.matrix[0].metric, "Deploy-ready code")

    def test_terminal_render_includes_priorities(self) -> None:
        brief = priority_matrix_bot.build_brief()
        text = priority_matrix_bot.render_terminal(brief)
        self.assertIn("[P0] AI Automation", text)
        self.assertIn("8-10am", text)

    def test_config_override_merges_over_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_path = Path(tmp_dir) / "config.json"
            cfg_path.write_text(
                json.dumps({"mantra": "Ship it.", "intelligence": ["Test signal."]}),
                encoding="utf-8",
            )
            config = priority_matrix_bot.load_config(cfg_path)
            brief = priority_matrix_bot.build_brief(config)
            self.assertEqual(brief.mantra, "Ship it.")
            self.assertEqual(brief.intelligence, ["Test signal."])
            # Untouched keys fall back to defaults.
            self.assertEqual(len(brief.matrix), 3)

    def test_write_outputs_creates_latest_and_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_dir = root / "operations" / "priority_matrix"
            archive_dir = output_dir / "archive"

            original_output = priority_matrix_bot.OUTPUT_DIR
            original_archive = priority_matrix_bot.ARCHIVE_DIR
            try:
                priority_matrix_bot.OUTPUT_DIR = output_dir
                priority_matrix_bot.ARCHIVE_DIR = archive_dir

                brief = priority_matrix_bot.build_brief()
                priority_matrix_bot.write_outputs(brief)

                self.assertTrue((output_dir / "latest.md").exists())
                self.assertTrue((output_dir / "latest.json").exists())
                self.assertGreater(len(list(archive_dir.glob("*.md"))), 0)
                self.assertGreater(len(list(archive_dir.glob("*.json"))), 0)

                payload = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["matrix"][0]["priority"], "P0")
            finally:
                priority_matrix_bot.OUTPUT_DIR = original_output
                priority_matrix_bot.ARCHIVE_DIR = original_archive


if __name__ == "__main__":
    unittest.main()
