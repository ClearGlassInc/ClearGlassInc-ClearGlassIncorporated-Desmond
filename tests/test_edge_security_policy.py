from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "infra" / "edge" / "scripts" / "validate_policy.py"
POLICY_PATH = ROOT / "infra" / "edge" / "policies" / "baseline.json"

spec = importlib.util.spec_from_file_location("edge_policy_validator", VALIDATOR_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def baseline() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


class EdgePolicySafetyTests(unittest.TestCase):
    def test_edge_baseline_policy_is_safe(self) -> None:
        self.assertEqual(validator.validate(baseline()), [])

    def test_geo_enforcement_cannot_be_enabled_in_baseline(self) -> None:
        policy = baseline()
        policy["defaults"]["geo_enforcement_enabled"] = True
        errors = validator.validate(policy)
        self.assertTrue(any("geo_enforcement_enabled must be false" in error for error in errors))

    def test_broad_terminal_block_is_rejected(self) -> None:
        policy = baseline()
        rule = copy.deepcopy(policy["rules"][0])
        rule.update(
            {
                "id": "test.broad-block",
                "priority": 99999,
                "scope": "all",
                "action": "block",
                "rollout_mode": "enforce",
                "category": "custom_waf",
                "description": "Unsafe broad block for regression testing only.",
                "rationale": "Regression test.",
            }
        )
        policy["rules"].append(rule)
        errors = validator.validate(policy)
        self.assertTrue(any("broad enabled block over scope=all is prohibited" in error for error in errors))

    def test_permanent_reputation_only_block_is_rejected(self) -> None:
        policy = baseline()
        rule = next(rule for rule in policy["rules"] if rule["category"] == "ip_reputation")
        rule["action"] = "block"
        rule["rollout_mode"] = "enforce"
        rule["expires_at"] = None
        errors = validator.validate(policy)
        self.assertTrue(any("reputation-only block requires expiry" in error for error in errors))

    def test_sensitive_logging_default_cannot_be_enabled(self) -> None:
        policy = baseline()
        policy["defaults"]["log_sensitive_fields"] = True
        errors = validator.validate(policy)
        self.assertTrue(any("log_sensitive_fields must be false" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
