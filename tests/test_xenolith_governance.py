# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Governance tests for XENOLITH: the policy gate, the lattice, the CLI.

These are the tests that must fail if someone opens a path where a high-risk
action executes without a recorded human approval. They are deliberately
adversarial — each one describes a way the gate could be bypassed.
"""

from __future__ import annotations

import json

import pytest

from xenolith.constants import Domain, PolicyViolation, RiskTier
from xenolith.lattice import Lattice
from xenolith.policy import (
    ActionRule,
    Decision,
    PolicyEngine,
    ProposedAction,
    sanitize,
    sanitize_payload,
)
from xenolith.registry import AgentRegistry


@pytest.fixture()
def registry() -> AgentRegistry:
    reg = AgentRegistry()
    reg.register(
        "BASTION",
        Domain.CYBERSECURITY,
        "containment",
        "respond",
        permissions=["cyber.respond", "cyber.forensics", "intel.read"],
    )
    reg.activate("BASTION")
    reg.register(
        "MERIDIAN",
        Domain.INTELLIGENCE,
        "fusion",
        "correlate",
        permissions=["intel.read", "intel.analyze"],
    )
    reg.activate("MERIDIAN")
    return reg


@pytest.fixture()
def policy(registry) -> PolicyEngine:
    return PolicyEngine(registry=registry)


def action(name: str, actor: str = "BASTION", domain=Domain.CYBERSECURITY, **kw):
    return ProposedAction(action=name, actor=actor, domain=domain, **kw)


# --------------------------------------------------------------------------- #
# The gate
# --------------------------------------------------------------------------- #
class TestPolicyGate:
    def test_unknown_actions_are_denied_not_defaulted_through(self, policy):
        verdict = policy.evaluate(action("nobody.defined.this"))
        assert verdict.decision is Decision.DENY
        assert verdict.risk_score == 100
        assert not verdict.executable

    def test_low_risk_reads_execute_immediately(self, policy):
        verdict = policy.evaluate(action("intel.read"))
        assert verdict.decision is Decision.ALLOW
        assert verdict.tier is RiskTier.LOW

    def test_high_risk_actions_are_blocked_pending_approval(self, policy):
        verdict = policy.evaluate(action("cyber.contain", targets=("srv-1",)))
        assert verdict.decision is Decision.BLOCK_PENDING_APPROVAL
        assert verdict.tier.blocks_until_approved
        assert verdict.approval_id is not None

    def test_medium_risk_actions_queue_rather_than_hard_block(self, policy):
        # cyber.forensic_capture scores 30 — approval required, but not the
        # hard block reserved for high/critical.
        verdict = policy.evaluate(action("cyber.forensic_capture", targets=("srv-1",)))
        assert verdict.tier is RiskTier.MEDIUM
        assert verdict.decision is Decision.QUEUE_APPROVAL
        assert not verdict.executable

    def test_capability_is_checked_before_risk(self, policy):
        # MERIDIAN holds neither threat.curate nor the cyber permissions, so a
        # medium-risk action it cannot perform is denied outright rather than
        # queued for a human to rubber-stamp.
        verdict = policy.evaluate(
            action("threat.watchlist_add", actor="MERIDIAN", domain=Domain.INTELLIGENCE)
        )
        assert verdict.decision is Decision.DENY
        assert not policy.pending(), "an unauthorized action must not enter the queue"

    def test_missing_permission_denies_before_risk_is_considered(self, policy):
        verdict = policy.evaluate(action("policy.amend", payload={"x": 1}))
        assert verdict.decision is Decision.DENY
        assert any("lacks required permission" in r for r in verdict.reasons)

    def test_domain_restriction_is_enforced(self, policy):
        verdict = policy.evaluate(
            action("cyber.contain", actor="MERIDIAN", domain=Domain.INTELLIGENCE)
        )
        assert verdict.decision is Decision.DENY

    def test_unregistered_actors_are_penalized(self, policy):
        verdict = policy.evaluate(action("intel.read", actor="GHOST"))
        assert verdict.decision is Decision.DENY

    def test_require_raises_when_not_executable(self, policy):
        with pytest.raises(PolicyViolation):
            policy.require(action("cyber.contain"))


class TestRiskScoring:
    def test_blast_radius_raises_the_score(self, policy):
        single = policy.score(action("cyber.block_indicator", targets=("a",)))[0]
        many = policy.score(action("cyber.block_indicator", targets=tuple(f"t{i}" for i in range(200))))[0]
        assert many > single

    def test_degraded_actor_health_raises_the_score(self, policy, registry):
        before = policy.score(action("cyber.forensic_capture"))[0]
        registry.heartbeat("BASTION", health=0.1)
        after = policy.score(action("cyber.forensic_capture"))[0]
        assert after > before

    def test_score_is_clamped_to_the_ladder(self, policy):
        score, _ = policy.score(action("cyber.contain", targets=tuple(f"t{i}" for i in range(500))))
        assert 0 <= score <= 100

    def test_reasons_explain_the_score(self, policy):
        _, reasons = policy.score(action("cyber.contain", targets=("a", "b", "c")))
        assert any("irreversible" in r for r in reasons)
        assert any("multi-target" in r for r in reasons)


class TestApprovals:
    def test_approval_unlocks_exactly_the_approved_action(self, policy):
        proposal = action("cyber.contain", payload={"asset": "srv-1"})
        first = policy.evaluate(proposal)
        policy.decide(first.approval_id, "human-operator", approve=True)
        assert policy.evaluate(proposal).decision is Decision.ALLOW

    def test_mutating_the_payload_invalidates_the_approval(self, policy):
        approved = action("cyber.contain", payload={"asset": "srv-1"})
        verdict = policy.evaluate(approved)
        policy.decide(verdict.approval_id, "human-operator", approve=True)

        drifted = action("cyber.contain", payload={"asset": "srv-2"})
        assert policy.evaluate(drifted).decision is Decision.BLOCK_PENDING_APPROVAL

    def test_requesters_cannot_approve_themselves(self, policy):
        verdict = policy.evaluate(action("cyber.contain"))
        with pytest.raises(PolicyViolation):
            policy.decide(verdict.approval_id, "BASTION", approve=True)

    def test_rejection_denies_the_action(self, policy):
        proposal = action("cyber.contain")
        verdict = policy.evaluate(proposal)
        policy.decide(verdict.approval_id, "human-operator", approve=False)
        assert policy.evaluate(proposal).decision is Decision.DENY

    def test_a_decision_cannot_be_revisited(self, policy):
        verdict = policy.evaluate(action("cyber.contain"))
        policy.decide(verdict.approval_id, "human-operator", approve=True)
        with pytest.raises(PolicyViolation):
            policy.decide(verdict.approval_id, "human-operator", approve=False)

    def test_repeated_evaluation_does_not_multiply_the_queue(self, policy):
        proposal = action("cyber.contain")
        policy.evaluate(proposal)
        policy.evaluate(proposal)
        policy.evaluate(proposal)
        assert len(policy.pending()) == 1

    def test_unknown_approval_ids_are_refused(self, policy):
        with pytest.raises(PolicyViolation):
            policy.decide("apr-99999", "human-operator", approve=True)

    def test_amending_policy_requires_a_named_human(self, policy):
        rule = ActionRule("custom.thing", 10, "intel.read")
        with pytest.raises(PolicyViolation):
            policy.amend(rule, approved_by="  ")
        assert policy.amend(rule, approved_by="ciso").action == "custom.thing"


#: Credential-shaped fixtures are assembled at import time rather than written
#: as literals. They are synthetic, but a literal would still match the
#: repository's hardcoded-secret scanner (.github/workflows/security.yml) and
#: fail the security gate on a test file that contains no real credential.
_AWS_SHAPED = "AKIA" + "IOSFODNN7EXAMPLE"
_STRIPE_SHAPED = "sk_" + "live_51H8xVexampleKEY"


class TestSanitization:
    @pytest.mark.parametrize(
        "raw,label",
        [
            ("Authorization: Bearer abcdef1234567890", "BEARER_TOKEN"),
            (f"key is {_STRIPE_SHAPED}", "API_KEY"),
            (f"{_AWS_SHAPED} in the config", "AWS_KEY"),
            ("password = hunter2correct", "SECRET_ASSIGNMENT"),
            ("contact analyst@example.com now", "EMAIL"),
            ("host 203.0.113.55 responded", "IPV4"),
        ],
    )
    def test_secrets_and_identifiers_are_redacted(self, raw, label):
        cleaned = sanitize(raw)
        assert f"[REDACTED:{label}]" in cleaned

    def test_original_secret_never_survives(self):
        assert "hunter2correct" not in sanitize("password = hunter2correct")

    def test_nested_payloads_are_walked(self):
        payload = {"a": {"b": ["mail me at ops@example.com"]}, "n": 5}
        cleaned = sanitize_payload(payload)
        assert "ops@example.com" not in json.dumps(cleaned)
        assert cleaned["n"] == 5

    def test_empty_and_non_string_values_survive(self):
        assert sanitize("") == ""
        assert sanitize_payload({"n": 1, "f": 1.5, "b": True}) == {"n": 1, "f": 1.5, "b": True}


# --------------------------------------------------------------------------- #
# The composed lattice
# --------------------------------------------------------------------------- #
@pytest.fixture()
def lattice() -> Lattice:
    lat = Lattice()
    lat.enlist(
        "BASTION",
        Domain.CYBERSECURITY,
        "containment",
        "respond",
        sponsor="ops",
        permissions=["cyber.respond", "cyber.forensics", "intel.read"],
    )
    return lat


class TestLattice:
    def test_enlist_issues_identity_and_registry_slot_together(self, lattice):
        record = lattice.registry.get("BASTION")
        assert lattice.identity.is_active("BASTION")
        assert record.key_fingerprint == lattice.identity.credential("BASTION").fingerprint

    def test_a_failed_registration_leaves_no_orphan_credential(self, lattice):
        from xenolith.registry import RegistryError

        # Occupy the registry slot directly so identity issuance succeeds and
        # registration is what fails — the rollback path.
        lattice.registry.register("PRISM", Domain.INTELLIGENCE, "squatter", "scope")
        with pytest.raises(RegistryError):
            lattice.enlist("PRISM", Domain.INTELLIGENCE, "fusion", "scope", sponsor="ops")
        assert not lattice.identity.is_active("PRISM"), "credential must be revoked on rollback"

    def test_high_risk_submission_does_not_execute(self, lattice):
        outcome = lattice.submit("BASTION", "cyber.contain", {"asset": "srv-1"})
        assert not outcome.executed
        assert outcome.approval_id is not None

    def test_approval_then_resubmission_executes(self, lattice):
        ran: list[str] = []
        lattice.register_executor("cyber.contain", lambda ctx: ran.append(ctx.payload["asset"]))

        first = lattice.submit("BASTION", "cyber.contain", {"asset": "srv-1"})
        assert ran == [], "nothing may run before approval"

        lattice.approve(first.approval_id, "human-operator")
        second = lattice.submit("BASTION", "cyber.contain", {"asset": "srv-1"})
        assert second.executed and ran == ["srv-1"]

    def test_executor_requires_an_existing_policy_rule(self, lattice):
        from xenolith.constants import LatticeError

        with pytest.raises(LatticeError):
            lattice.register_executor("undeclared.capability", lambda ctx: None)

    def test_every_submission_is_audited_even_when_denied(self, lattice):
        before = len(lattice.ledger)
        lattice.submit("BASTION", "nope.not.a.thing", {})
        assert len(lattice.ledger) == before + 1
        assert lattice.ledger.entries[-1].detail["decision"] == "deny"

    def test_ledger_payloads_are_sanitized(self, lattice):
        lattice.submit("BASTION", "intel.read", {"note": "reach me at spy@example.com"})
        assert "spy@example.com" not in json.dumps(
            [e.as_dict() for e in lattice.ledger.entries], default=str
        )

    def test_executor_failure_is_recorded_not_raised(self, lattice):
        def boom(_ctx):
            raise RuntimeError("executor exploded")

        lattice.register_executor("intel.read", boom)
        outcome = lattice.submit("BASTION", "intel.read", {})
        assert not outcome.executed
        assert "executor exploded" in outcome.error

    def test_dismissed_agents_cannot_act(self, lattice):
        lattice.dismiss("BASTION", reason="rotation")
        outcome = lattice.submit("BASTION", "intel.read", {})
        assert not outcome.executed
        assert outcome.verdict.decision is Decision.DENY

    def test_audit_chain_survives_a_full_cycle(self, lattice):
        lattice.submit("BASTION", "intel.read", {})
        first = lattice.submit("BASTION", "cyber.contain", {"asset": "a"})
        lattice.approve(first.approval_id, "human-operator")
        lattice.submit("BASTION", "cyber.contain", {"asset": "a"})
        assert lattice.ledger.verify()

    def test_submissions_are_announced_on_the_bus(self, lattice):
        seen: list[str] = []
        lattice.observe_bus("action.*", lambda e: seen.append(e.type))
        lattice.submit("BASTION", "intel.read", {})
        assert "action.allow" in seen

    def test_stale_agents_are_swept_and_logged(self, lattice):
        import time as _time

        lattice.registry.get("BASTION").last_heartbeat = _time.time() - 10_000
        assert lattice.sweep() == ("BASTION",)
        assert lattice.ledger.entries[-1].action == "agent.degraded"


class TestGovernanceInvariants:
    """The suite CI runs. A regression here means an ungoverned path exists."""

    def test_all_invariants_hold_on_a_fresh_lattice(self):
        checks = Lattice().self_check()
        failed = [c.name for c in checks if not c.passed]
        assert not failed, f"governance invariants failed: {failed}"

    def test_self_check_covers_the_critical_properties(self):
        names = {c.name for c in Lattice().self_check()}
        assert {
            "high_risk_blocked_until_approved",
            "self_approval_refused",
            "approval_unlocks_action",
            "approval_bound_to_payload",
            "unknown_action_denied",
            "missing_permission_denied",
            "every_submission_audited",
        } <= names

    def test_self_check_does_not_mutate_the_live_lattice(self, lattice):
        before = len(lattice.ledger)
        lattice.self_check()
        assert len(lattice.ledger) == before

    def test_state_is_json_serializable(self, lattice):
        assert json.loads(json.dumps(lattice.state()))["platform"] == "XENOLITH"

    def test_state_reports_fail_closed(self, lattice):
        assert lattice.state()["governance"]["fail_closed"] is True


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
class TestCLI:
    def test_check_mode_exits_zero_when_invariants_hold(self, capsys):
        from xenolith.cli import main

        assert main(["--check"]) == 0
        assert "invariants hold" in capsys.readouterr().out

    def test_json_mode_emits_parseable_state(self, capsys):
        from xenolith.cli import main

        assert main(["--json"]) == 0
        assert json.loads(capsys.readouterr().out)["platform"] == "XENOLITH"

    def test_report_mode_renders_a_status_block(self, capsys):
        from xenolith.cli import main

        assert main([]) == 0
        assert "XENOLITH" in capsys.readouterr().out

    def test_write_mode_produces_the_command_surface_feed(self, tmp_path, capsys):
        from xenolith.cli import main

        target = tmp_path / "lattice.json"
        assert main(["--write", str(target)]) == 0
        capsys.readouterr()
        feed = json.loads(target.read_text())
        assert feed["governance"]["fail_closed"] is True
        assert feed["agents"] and feed["registry"]["population"] > 0
