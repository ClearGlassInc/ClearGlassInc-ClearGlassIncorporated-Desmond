# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import tempfile
import unittest
from pathlib import Path

from bots import repo_task_audit_bot


class RepoTaskAuditBotTests(unittest.TestCase):
    def test_collect_bot_tasks_filters_checkbox_and_bot_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "notes.md").write_text(
                "\n".join(
                    [
                        "- [ ] bot should process source A",
                        "- [x] Agent finished data sync",
                        "- [ ] human follow-up",
                    ]
                ),
                encoding="utf-8",
            )

            tasks = repo_task_audit_bot.collect_bot_tasks(root)
            self.assertEqual(len(tasks), 2)
            self.assertFalse(tasks[0].done)
            self.assertTrue(tasks[1].done)

    def test_run_writes_outputs_with_pending_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "todo.md").write_text("- [ ] bot triage queue\n", encoding="utf-8")

            original_output = repo_task_audit_bot.OUTPUT_DIR
            original_archive = repo_task_audit_bot.ARCHIVE_DIR
            try:
                repo_task_audit_bot.OUTPUT_DIR = root / "operations" / "output" / "repo_task_audit"
                repo_task_audit_bot.ARCHIVE_DIR = repo_task_audit_bot.OUTPUT_DIR / "archive"

                status = repo_task_audit_bot.run(root)
                latest_md = repo_task_audit_bot.OUTPUT_DIR / "latest.md"
                latest_json = repo_task_audit_bot.OUTPUT_DIR / "latest.json"

                self.assertTrue(latest_md.exists())
                self.assertTrue(latest_json.exists())
                self.assertEqual(status.bot_task_pending, 1)
                self.assertIn("Pending bot tasks", latest_md.read_text(encoding="utf-8"))
            finally:
                repo_task_audit_bot.OUTPUT_DIR = original_output
                repo_task_audit_bot.ARCHIVE_DIR = original_archive


if __name__ == "__main__":
    unittest.main()
