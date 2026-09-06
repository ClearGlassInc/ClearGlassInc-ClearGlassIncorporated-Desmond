# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import tempfile
import unittest
from pathlib import Path

from bots import marketing_bot


class MarketingBotOutputTests(unittest.TestCase):
    def test_archive_file_uses_full_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_dir = root / "marketing" / "output"
            archive_dir = output_dir / "archive"

            original_root = marketing_bot.ROOT
            original_output = marketing_bot.OUTPUT_DIR
            original_archive = marketing_bot.ARCHIVE_DIR
            try:
                marketing_bot.ROOT = root
                marketing_bot.OUTPUT_DIR = output_dir
                marketing_bot.ARCHIVE_DIR = archive_dir

                status = marketing_bot.MarketingStatus(
                    run_utc="2026-04-24T16:23:45+00:00",
                    pillar="brand",
                    facebook_enabled=True,
                    facebook_ready=False,
                    page_id_present=False,
                    token_present=False,
                    output_dir="marketing/output",
                )

                marketing_bot.write_outputs(status)
                expected = archive_dir / "2026-04-24T162345Z.md"
                self.assertTrue(expected.exists(), f"Expected archive output {expected} to exist")
            finally:
                marketing_bot.ROOT = original_root
                marketing_bot.OUTPUT_DIR = original_output
                marketing_bot.ARCHIVE_DIR = original_archive


if __name__ == "__main__":
    unittest.main()
