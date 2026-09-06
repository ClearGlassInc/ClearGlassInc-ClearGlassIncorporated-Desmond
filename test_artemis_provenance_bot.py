# Copyright (c) 2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bots import artemis_provenance_bot as bot


class ArtemisProvenanceBotTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._original_root = bot.ROOT
        self._original_output = bot.OUTPUT_DIR
        bot.ROOT = self.root
        bot.OUTPUT_DIR = self.root / "operations" / "artemis"
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        bot.ROOT = self._original_root
        bot.OUTPUT_DIR = self._original_output

    def _write_artifact(self, rel: str, content: bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_manifest_records_real_checksums(self) -> None:
        content = b"ARTEMIS provenance test artifact\n"
        self._write_artifact("NOTICE", content)
        manifest = bot.build_manifest()
        entries = {e["artifact"]: e for e in manifest["artifacts"]}
        self.assertIn("NOTICE", entries)
        self.assertEqual(entries["NOTICE"]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(entries["NOTICE"]["size_bytes"], len(content))
        self.assertEqual(manifest["artifact_count"], len(manifest["artifacts"]))
        self.assertEqual(manifest["organization"], "ClearGlass Inc.")
        self.assertEqual(manifest["original_author"], "Desmond Otieno Odhiambo")

    def test_missing_git_metadata_is_null_not_fabricated(self) -> None:
        # The temp tree is not a git repository, so commit fields must be
        # recorded as None rather than invented values.
        self._write_artifact("TRADEMARKS.md", b"marks\n")
        manifest = bot.build_manifest()
        entry = next(e for e in manifest["artifacts"] if e["artifact"] == "TRADEMARKS.md")
        self.assertIsNone(entry["last_commit"])
        self.assertIsNone(entry["last_commit_date"])
        self.assertIsNone(manifest["repository_head"])

    def test_main_writes_manifest_json(self) -> None:
        self._write_artifact("docs/PROVENANCE.md", b"policy\n")
        self.assertEqual(bot.main(), 0)
        out_path = bot.OUTPUT_DIR / "provenance_manifest.json"
        self.assertTrue(out_path.exists())
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["system"], "ARTEMIS")
        self.assertGreaterEqual(payload["artifact_count"], 1)


if __name__ == "__main__":
    unittest.main()
