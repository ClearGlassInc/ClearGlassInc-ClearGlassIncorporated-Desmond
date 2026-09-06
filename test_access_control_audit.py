# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for the defensive access-control audit harness.

These exercise pure logic and safety gates only — no network calls are made.
"""

from __future__ import annotations

import copy
import unittest

from scripts import access_control_audit as aca


class SwapNumericIdTests(unittest.TestCase):
    def test_swaps_trailing_path_id(self) -> None:
        url, changed = aca.swap_numeric_id("https://h.test/api/users/123")
        self.assertTrue(changed)
        self.assertEqual(url, "https://h.test/api/users/124")

    def test_swaps_query_id_when_no_path_id(self) -> None:
        url, changed = aca.swap_numeric_id("https://h.test/api/doc?owner_id=7")
        self.assertTrue(changed)
        self.assertEqual(url, "https://h.test/api/doc?owner_id=8")

    def test_no_numeric_id_leaves_url_unchanged(self) -> None:
        url, changed = aca.swap_numeric_id("https://h.test/api/me")
        self.assertFalse(changed)
        self.assertEqual(url, "https://h.test/api/me")


class HostClassificationTests(unittest.TestCase):
    def test_placeholder_hosts_detected(self) -> None:
        self.assertTrue(aca.is_placeholder_host("https://example.com/x"))
        self.assertTrue(aca.is_placeholder_host("http://localhost:8080/x"))

    def test_real_host_not_placeholder(self) -> None:
        self.assertFalse(aca.is_placeholder_host("https://api.acme.test/x"))


class HeaderBuildingTests(unittest.TestCase):
    def test_cookies_collapse_into_cookie_header(self) -> None:
        headers = aca.build_headers({"headers": {"X-A": "1"}, "cookies": {"s": "abc", "t": "def"}})
        self.assertEqual(headers["X-A"], "1")
        self.assertEqual(headers["Cookie"], "s=abc; t=def")

    def test_none_account_yields_no_auth(self) -> None:
        headers = aca.build_headers(None)
        self.assertNotIn("Cookie", headers)
        self.assertNotIn("Authorization", headers)


class AuthorizationGateTests(unittest.TestCase):
    def _base_cfg(self) -> dict:
        cfg = copy.deepcopy(aca.CONFIG_TEMPLATE)
        cfg["authorization"]["confirmed"] = True
        cfg["authorization"]["scope"] = "authorized lab scope"
        cfg["endpoints"][0]["url"] = "https://api.acme.test/v1/orders/456"
        return cfg

    def test_template_default_is_inert(self) -> None:
        # Shipped template: not confirmed + placeholder host -> must refuse.
        errors = aca.validate_config(copy.deepcopy(aca.CONFIG_TEMPLATE), allow_placeholder=False)
        self.assertTrue(errors)

    def test_unconfirmed_authorization_blocks(self) -> None:
        cfg = self._base_cfg()
        cfg["authorization"]["confirmed"] = False
        errors = aca.validate_config(cfg, allow_placeholder=False)
        self.assertTrue(any("authorization.confirmed" in e for e in errors))

    def test_placeholder_host_blocks_without_optin(self) -> None:
        cfg = self._base_cfg()
        cfg["endpoints"][0]["url"] = "https://example.com/v1/orders/456"
        errors = aca.validate_config(cfg, allow_placeholder=False)
        self.assertTrue(any("placeholder host" in e for e in errors))

    def test_write_method_blocks_without_optin(self) -> None:
        cfg = self._base_cfg()
        cfg["endpoints"][0]["method"] = "DELETE"
        errors = aca.validate_config(cfg, allow_placeholder=False)
        self.assertTrue(any("write method" in e for e in errors))

    def test_valid_authorized_config_passes(self) -> None:
        errors = aca.validate_config(self._base_cfg(), allow_placeholder=False)
        self.assertEqual(errors, [])


class BudgetTests(unittest.TestCase):
    def test_budget_caps_requests(self) -> None:
        budget = aca.Budget(max_requests=2, delay_seconds=0)
        self.assertTrue(budget.spend())
        self.assertTrue(budget.spend())
        self.assertFalse(budget.spend())


if __name__ == "__main__":
    unittest.main()
