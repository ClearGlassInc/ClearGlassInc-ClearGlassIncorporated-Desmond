# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bots import artemis_growth_bot


class ArtemisGrowthBotTests(unittest.TestCase):
    def test_campaign_links_are_allowlisted_and_tagged(self) -> None:
        for asset in artemis_growth_bot.build_campaign_assets():
            parsed = urlparse(asset.destination)
            self.assertEqual(parsed.scheme, "https")
            self.assertIn(parsed.hostname, artemis_growth_bot.ALLOWED_HOSTS)
            query = parse_qs(parsed.query)
            self.assertEqual(query["utm_campaign"], ["artemis_launch"])
            self.assertTrue(query["utm_source"][0])
            self.assertTrue(query["utm_medium"][0])
            self.assertTrue(query["utm_content"][0])
            self.assertTrue(asset.review_required)
            self.assertTrue(asset.evidence)

    def test_generated_copy_rejects_fabricated_and_manipulative_patterns(self) -> None:
        combined = "\n".join(
            asset.copy for asset in artemis_growth_bot.build_campaign_assets()
        )
        combined += "\n" + "\n".join(
            tweet.text
            for thread in artemis_growth_bot.build_threads()
            for tweet in thread.tweets
        )

        banned = (
            "signed deal",
            "gave me my reputation back",
            "guaranteed",
            "buy a star",
            "star for reward",
            "mass-message",
        )
        lowered = combined.lower()
        for phrase in banned:
            self.assertNotIn(phrase, lowered)

    def test_campaign_link_rejects_non_allowlisted_destination(self) -> None:
        link = artemis_growth_bot.CampaignLink(
            destination="https://example.com/",
            source="github",
            medium="readme",
            campaign="artemis_launch",
            content="test",
        )
        with self.assertRaises(ValueError):
            link.render()

    def test_write_outputs_creates_review_gated_campaign_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_dir = root / "marketing" / "output"
            archive_dir = output_dir / "threads_archive"
            site_page = root / "threads.html"

            originals = {
                "ROOT": artemis_growth_bot.ROOT,
                "OUTPUT_DIR": artemis_growth_bot.OUTPUT_DIR,
                "THREADS_ARCHIVE_DIR": artemis_growth_bot.THREADS_ARCHIVE_DIR,
                "SITE_PAGE": artemis_growth_bot.SITE_PAGE,
                "THREADS_JSON": artemis_growth_bot.THREADS_JSON,
                "THREADS_MD": artemis_growth_bot.THREADS_MD,
                "CAMPAIGN_JSON": artemis_growth_bot.CAMPAIGN_JSON,
                "CAMPAIGN_MD": artemis_growth_bot.CAMPAIGN_MD,
            }

            try:
                artemis_growth_bot.ROOT = root
                artemis_growth_bot.OUTPUT_DIR = output_dir
                artemis_growth_bot.THREADS_ARCHIVE_DIR = archive_dir
                artemis_growth_bot.SITE_PAGE = site_page
                artemis_growth_bot.THREADS_JSON = output_dir / "threads_latest.json"
                artemis_growth_bot.THREADS_MD = output_dir / "threads_latest.md"
                artemis_growth_bot.CAMPAIGN_JSON = output_dir / "campaign_latest.json"
                artemis_growth_bot.CAMPAIGN_MD = output_dir / "campaign_latest.md"

                run = artemis_growth_bot.write_outputs("ClearGlassInc Artemis")

                self.assertEqual(run.total_threads, 5)
                self.assertEqual(run.total_assets, 5)
                self.assertEqual(run.publication_mode, "manual-review-only")
                self.assertTrue(site_page.exists())
                self.assertTrue((output_dir / "threads_latest.md").exists())
                self.assertTrue((output_dir / "threads_latest.json").exists())
                self.assertTrue((output_dir / "campaign_latest.md").exists())
                self.assertTrue((output_dir / "campaign_latest.json").exists())
                self.assertEqual(len(list(archive_dir.glob("*.md"))), 1)

                campaign_data = json.loads(
                    (output_dir / "campaign_latest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(
                    campaign_data["run"]["publication_mode"],
                    "manual-review-only",
                )
                self.assertTrue(
                    all(asset["review_required"] for asset in campaign_data["assets"])
                )

                site = site_page.read_text(encoding="utf-8")
                self.assertIn("DRAFT — HUMAN REVIEW REQUIRED", site)
                self.assertIn('name="robots" content="noindex,nofollow"', site)
            finally:
                for name, value in originals.items():
                    setattr(artemis_growth_bot, name, value)


if __name__ == "__main__":
    unittest.main()
