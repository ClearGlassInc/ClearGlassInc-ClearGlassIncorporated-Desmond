from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from agent_army.orchestrator import AgentArmy, ConfigurationError, load_config, main


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "agent_army" / "config.json"


class AgentArmyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(CONFIG_PATH)
        cls.army = AgentArmy(cls.config)

    def test_config_covers_required_divisions(self) -> None:
        divisions = {role["division"] for role in self.config["roles"]}
        self.assertTrue({"command", "engineering", "marketing"}.issubset(divisions))

    def test_combined_request_routes_engineering_and_marketing(self) -> None:
        selected = set(
            self.army.select_roles(
                "Build and test a secure API, then launch a marketing campaign tied to revenue."
            )
        )
        self.assertTrue(
            {
                "chief_of_staff",
                "staff_engineer",
                "quality_security",
                "market_intelligence",
                "content_strategist",
                "distribution_planner",
                "revenue_operator",
                "analytics_controller",
            }.issubset(selected)
        )

    def test_legacy_marketing_bot_army_routes_specialists(self) -> None:
        selected = set(
            self.army.select_roles(
                "Add a bot army for a marketing compaign while preserving the legacy system."
            )
        )
        self.assertTrue(
            {
                "chief_of_staff",
                "legacy_modernization",
                "market_intelligence",
                "content_strategist",
                "campaign_bot_commander",
                "distribution_planner",
                "analytics_controller",
            }.issubset(selected)
        )

    def test_external_side_effects_create_approval_gates(self) -> None:
        approvals = set(
            self.army.required_approvals(
                "Deploy to production, publish the launch, email prospects, and spend on ads."
            )
        )
        self.assertEqual(
            approvals,
            {
                "production_deploy",
                "external_publish",
                "external_outreach",
                "paid_spend",
            },
        )

    def test_planning_only_request_does_not_require_external_approval(self) -> None:
        plan = self.army.plan("Create an internal architecture and campaign planning brief.")
        self.assertEqual(plan.approvals_required, ())
        self.assertGreaterEqual(len(plan.steps), 4)

    def test_plan_id_is_deterministic(self) -> None:
        first = self.army.plan("Build a reliable product launch system.")
        second = self.army.plan("Build a reliable product launch system.")
        self.assertEqual(first.plan_id, second.plan_id)

    def test_duplicate_role_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.config)
        invalid["roles"].append(copy.deepcopy(invalid["roles"][0]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(path)

    def test_cli_writes_valid_json_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plan.json"
            exit_code = main(
                [
                    "--request",
                    "Build and validate a marketing analytics service.",
                    "--config",
                    str(CONFIG_PATH),
                    "--format",
                    "json",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["system"], self.config["system"])
            self.assertTrue(payload["steps"])
            self.assertFalse(output.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
