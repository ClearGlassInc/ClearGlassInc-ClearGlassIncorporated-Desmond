# Copyright (c) 2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""CI gate: every agent must declare a machine-checkable permission scope.

Background in ``operations/architect-checklist/2026-W31.md`` (item 3). The week-31
audit found that agent permission declarations were inconsistent *and* inverted:
the twelve narrowest agents declared clean scopes, while the broadest-authority
agents — executive, agent OS, execution, workflow repair — declared none at all
and expressed their limits as prose in ``safety_model``/``guardrails``. Prose is
not a control: it cannot be tested and it degrades silently.

These tests make the declaration mandatory and the vocabulary closed, so a new
agent cannot ship without a scope and an existing one cannot quietly invent a
capability token nobody has agreed to.
"""
import json
import unittest

from agents import permissions as perms


class AgentManifestsAreWellFormed(unittest.TestCase):
    def setUp(self):
        self.paths = perms.agent_manifest_paths()

    def test_at_least_one_agent_is_discovered(self):
        # Guards against the glob silently matching nothing, which would make
        # every other test in this file vacuously pass.
        self.assertGreater(len(self.paths), 0, "no agents/*/agent.json found")

    def test_every_manifest_is_valid_json(self):
        for path in self.paths:
            with self.subTest(agent=path.parent.name):
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    self.fail(f"{path} is not valid JSON: {exc}")


class EveryAgentDeclaresAScope(unittest.TestCase):
    def setUp(self):
        self.scopes = perms.load_agent_scopes()

    def test_permissions_key_present_and_non_empty(self):
        for name, manifest in self.scopes.items():
            with self.subTest(agent=name):
                self.assertIn(
                    "permissions",
                    manifest,
                    f"agent '{name}' declares no permissions. Add a "
                    f"'permissions' list — see agents/permissions.py for the "
                    f"accepted vocabulary.",
                )
                self.assertIsInstance(manifest["permissions"], list)
                self.assertGreater(
                    len(manifest["permissions"]), 0,
                    f"agent '{name}' declares an empty permission list",
                )

    def test_permission_tokens_are_strings(self):
        for name, manifest in self.scopes.items():
            for token in manifest.get("permissions", []):
                with self.subTest(agent=name, token=token):
                    self.assertIsInstance(token, str)

    def test_permission_tokens_come_from_the_known_vocabulary(self):
        for name, manifest in self.scopes.items():
            unknown = perms.unknown_capabilities(manifest.get("permissions", []))
            with self.subTest(agent=name):
                self.assertEqual(
                    unknown, [],
                    f"agent '{name}' uses capability token(s) {unknown} that are "
                    f"not in agents/permissions.py. Either use an existing token "
                    f"or add the new one to CANONICAL_CAPABILITIES deliberately.",
                )

    def test_external_action_approval_flag_is_declared(self):
        for name, manifest in self.scopes.items():
            with self.subTest(agent=name):
                self.assertIn(
                    "approval_required_for_external_actions", manifest,
                    f"agent '{name}' does not state whether external actions "
                    f"need approval",
                )
                self.assertIsInstance(
                    manifest["approval_required_for_external_actions"], bool
                )

    def test_forbidden_list_is_declared_and_non_empty(self):
        for name, manifest in self.scopes.items():
            with self.subTest(agent=name):
                self.assertIn("forbidden", manifest, f"agent '{name}' has no 'forbidden' list")
                self.assertIsInstance(manifest["forbidden"], list)
                self.assertGreater(len(manifest["forbidden"]), 0)


class VocabularyIsInternallyConsistent(unittest.TestCase):
    def test_legacy_and_canonical_do_not_overlap(self):
        self.assertEqual(
            perms.CANONICAL_CAPABILITIES & perms.LEGACY_CAPABILITIES, frozenset()
        )

    def test_non_mutating_is_a_subset_of_canonical(self):
        self.assertTrue(
            perms.NON_MUTATING_CAPABILITIES <= perms.CANONICAL_CAPABILITIES,
            "NON_MUTATING_CAPABILITIES contains tokens absent from the canonical set",
        )

    def test_legacy_set_is_closed(self):
        # The legacy tokens are grandfathered, not a growth area. If this count
        # rises, someone has added free-text capabilities instead of using the
        # canonical vocabulary.
        self.assertEqual(
            len(perms.LEGACY_CAPABILITIES), 5,
            "the legacy capability set is closed — new agents must use "
            "CANONICAL_CAPABILITIES",
        )

    def test_every_declared_token_is_actually_used_or_documented(self):
        # Catches vocabulary rot in the other direction: a canonical token that
        # no agent uses is either dead or a typo nobody noticed.
        used = {
            token
            for manifest in perms.load_agent_scopes().values()
            for token in manifest.get("permissions", [])
        }
        unused = perms.CANONICAL_CAPABILITIES - used
        self.assertEqual(
            unused, frozenset(),
            f"canonical capabilities declared but unused by any agent: {sorted(unused)}",
        )


if __name__ == "__main__":
    unittest.main()
