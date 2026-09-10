import json
import tempfile
import unittest
from pathlib import Path

from bots import guardian_artemis_sales_bot as bot


class GuardianArtemisSalesBotTests(unittest.TestCase):
    def test_run_covers_all_audiences(self) -> None:
        run = bot.build_run()
        keys = {n.audience_key for n in run.narratives}
        self.assertEqual(keys, {"investors", "enterprise", "government"})
        self.assertEqual(run.total_audiences, 3)

    def test_each_narrative_contains_required_artifacts(self) -> None:
        run = bot.build_run()
        for n in run.narratives:
            self.assertTrue(n.long_pitch.strip(), f"long pitch missing for {n.audience_key}")
            self.assertTrue(n.elevator_pitch.strip(), f"elevator missing for {n.audience_key}")
            self.assertTrue(n.investor_hook.strip(), f"investor hook missing for {n.audience_key}")
            self.assertGreaterEqual(len(n.guardian_taglines), 3)
            self.assertGreaterEqual(len(n.artemis_taglines), 3)
            self.assertIn("Project Guardian", n.long_pitch)
            self.assertIn("Project Artemis", n.long_pitch)

    def test_markdown_renders_all_sections(self) -> None:
        run = bot.build_run()
        md = bot.build_markdown(run)
        self.assertIn("Guardian & Artemis Sales Brain Output", md)
        self.assertIn("Long-Form Pitch", md)
        self.assertIn("30-Second Elevator Pitch", md)
        self.assertIn("Investor / Partner Hook", md)
        self.assertIn("Tagline Options", md)
        for label in ("Investors", "Enterprise & Financial Institutions", "Government & Defense"):
            self.assertIn(label, md)

    def test_write_outputs_creates_latest_and_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "marketing" / "output" / "sales_guardian_artemis"
            archive_dir = output_dir / "archive"

            original_root = bot.ROOT
            original_output = bot.OUTPUT_DIR
            original_archive = bot.ARCHIVE_DIR
            original_prompt = bot.PROMPT_PATH
            try:
                bot.ROOT = root
                bot.OUTPUT_DIR = output_dir
                bot.ARCHIVE_DIR = archive_dir
                bot.PROMPT_PATH = root / "prompts" / "sales_guardian_artemis_system_prompt.md"

                run = bot.build_run()
                md_path, json_path = bot.write_outputs(run)

                self.assertTrue(md_path.exists())
                self.assertTrue(json_path.exists())
                self.assertGreater(len(list(archive_dir.glob("*.md"))), 0)
                self.assertGreater(len(list(archive_dir.glob("*.json"))), 0)

                payload = json.loads(json_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["total_audiences"], 3)
                self.assertEqual(len(payload["narratives"]), 3)
            finally:
                bot.ROOT = original_root
                bot.OUTPUT_DIR = original_output
                bot.ARCHIVE_DIR = original_archive
                bot.PROMPT_PATH = original_prompt


if __name__ == "__main__":
    unittest.main()
