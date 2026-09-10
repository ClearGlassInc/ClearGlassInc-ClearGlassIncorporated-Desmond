# Copyright (c) 2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import tempfile
import unittest
from pathlib import Path

from bots import artemis_ip_guardian_bot as bot

ATTRIBUTED = "ClearGlass Inc — Desmond Otieno Odhiambo\n"


def _populate_compliant_tree(root: Path) -> None:
    for rel in bot.REQUIRED_GOVERNANCE_FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ATTRIBUTED, encoding="utf-8")
    for agent in ("artemis_command_system", "artemis_ip_guardian"):
        agent_dir = root / "agents" / agent
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "agent.json").write_text(
            '{"owner": "ClearGlass Inc.", "original_author": "Desmond Otieno Odhiambo",'
            ' "system_prompt_path": "system_prompt.md"}\n',
            encoding="utf-8",
        )
        (agent_dir / "system_prompt.md").write_text(ATTRIBUTED, encoding="utf-8")


class ArtemisIpGuardianBotTests(unittest.TestCase):
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

    def test_compliant_tree_passes_strict(self) -> None:
        _populate_compliant_tree(self.root)
        exit_code = bot.main(["--strict"])
        self.assertEqual(exit_code, 0)
        report_path = bot.OUTPUT_DIR / "ip_guardian_report.json"
        self.assertTrue(report_path.exists())
        self.assertTrue((bot.OUTPUT_DIR / "ip_guardian_report.md").exists())

    def test_missing_governance_file_fails_closed_in_strict_mode(self) -> None:
        _populate_compliant_tree(self.root)
        (self.root / "NOTICE").unlink()
        self.assertEqual(bot.main(["--strict"]), 1)
        # Report-only mode records the failure but does not fail the gate.
        self.assertEqual(bot.main([]), 0)

    def test_missing_attribution_marker_is_detected(self) -> None:
        _populate_compliant_tree(self.root)
        prompt = self.root / "agents" / "artemis_command_system" / "system_prompt.md"
        prompt.write_text("no attribution here\n", encoding="utf-8")
        report = bot.GuardianReport(run_utc="test", strict=True)
        bot.check_attribution_headers(report)
        failures = [c for c in report.checks if c.status == "fail"]
        self.assertTrue(any("system_prompt.md" in c.target for c in failures))
        self.assertEqual(report.status, "fail")

    def test_agent_config_with_dangling_prompt_fails(self) -> None:
        _populate_compliant_tree(self.root)
        (self.root / "agents" / "artemis_ip_guardian" / "system_prompt.md").unlink()
        report = bot.GuardianReport(run_utc="test", strict=False)
        bot.check_agent_configs(report)
        self.assertEqual(report.status, "fail")

    def test_markdown_report_states_overall_status(self) -> None:
        report = bot.GuardianReport(run_utc="test", strict=True)
        report.add("governance-file", "LICENSE", True)
        md = bot.render_markdown(report)
        self.assertIn("**PASS**", md)
        self.assertIn("| governance-file | `LICENSE` | pass |", md)


if __name__ == "__main__":
    unittest.main()
