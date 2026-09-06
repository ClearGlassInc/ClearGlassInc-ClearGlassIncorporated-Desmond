import json
import tempfile
import unittest
from pathlib import Path

from bots import artemis_daily_priority_bot


class ArtemisDailyPriorityBotTests(unittest.TestCase):
    def test_build_markdown_contains_priority_matrix(self) -> None:
        brief = artemis_daily_priority_bot.build_daily_brief()
        md = artemis_daily_priority_bot.build_markdown(brief)
        self.assertIn("TODAY'S STRATEGIC PRIORITY MATRIX", md)
        self.assertIn("| P0 | AI Automation |", md)

    def test_write_outputs_creates_latest_and_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_dir = root / "operations" / "daily_priority"
            archive_dir = output_dir / "archive"

            original_root = artemis_daily_priority_bot.ROOT
            original_output = artemis_daily_priority_bot.OUTPUT_DIR
            original_archive = artemis_daily_priority_bot.ARCHIVE_DIR
            try:
                artemis_daily_priority_bot.ROOT = root
                artemis_daily_priority_bot.OUTPUT_DIR = output_dir
                artemis_daily_priority_bot.ARCHIVE_DIR = archive_dir

                brief = artemis_daily_priority_bot.build_daily_brief()
                artemis_daily_priority_bot.write_outputs(brief)

                self.assertTrue((output_dir / "latest.md").exists())
                self.assertTrue((output_dir / "latest.json").exists())
                self.assertGreater(len(list(archive_dir.glob("*.md"))), 0)
                self.assertGreater(len(list(archive_dir.glob("*.json"))), 0)

                payload = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["strategic_priorities"][0]["priority"], "P0")
            finally:
                artemis_daily_priority_bot.ROOT = original_root
                artemis_daily_priority_bot.OUTPUT_DIR = original_output
                artemis_daily_priority_bot.ARCHIVE_DIR = original_archive


if __name__ == "__main__":
    unittest.main()
