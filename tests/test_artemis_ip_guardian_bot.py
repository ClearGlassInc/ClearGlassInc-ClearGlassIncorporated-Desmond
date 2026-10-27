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

    def test_codeowners_is_found_where_github_reads_it(self) -> None:
        _populate_compliant_tree(self.root)
        for rel in bot.CODEOWNERS_LOCATIONS:
            (self.root / rel).unlink(missing_ok=True)
        for rel in bot.CODEOWNERS_LOCATIONS:
            with self.subTest(location=rel):
                path = self.root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("* @ClearGlassInc\n", encoding="utf-8")
                report = bot.GuardianReport(run_utc="test", strict=True)
                bot.check_governance_files(report)
                self.assertEqual(report.status, "pass", report.checks)
                path.unlink()

    def test_empty_github_codeowners_shadows_the_root_file(self) -> None:
        # GitHub uses the first CODEOWNERS it finds, so an empty .github/ copy
        # leaves the repository with no owners even when the root file is set.
        _populate_compliant_tree(self.root)
        (self.root / "CODEOWNERS").write_text("* @ClearGlassInc\n", encoding="utf-8")
        (self.root / ".github").mkdir(exist_ok=True)
        (self.root / ".github" / "CODEOWNERS").write_text("", encoding="utf-8")
        report = bot.GuardianReport(run_utc="test", strict=True)
        bot.check_governance_files(report)
        failed = [c.target for c in report.checks if c.status == "fail"]
        self.assertEqual(failed, [".github/CODEOWNERS"])

    def test_this_repository_passes_the_gate(self) -> None:
        # The other tests build their tree from REQUIRED_GOVERNANCE_FILES, so a
        # wrong path there passes them all. Since the 2026-09-06 upload left
        # docs/PROVENANCE.md and docs/IP-POLICY.md at the root, the strict gate
        # in artemis-deploy.yml failed every run while this suite stayed green.
        bot.ROOT = self._original_root
        report = bot.GuardianReport(run_utc="test", strict=True)
        bot.check_governance_files(report)
        bot.check_attribution_headers(report)
        bot.check_agent_configs(report)
        failed = [(c.check, c.target, c.detail) for c in report.checks if c.status == "fail"]
        self.assertEqual(failed, [])

    def test_markdown_report_states_overall_status(self) -> None:
        report = bot.GuardianReport(run_utc="test", strict=True)
        report.add("governance-file", "LICENSE", True)
        md = bot.render_markdown(report)
        self.assertIn("**PASS**", md)
        self.assertIn("| governance-file | `LICENSE` | pass |", md)


if __name__ == "__main__":
    unittest.main()
