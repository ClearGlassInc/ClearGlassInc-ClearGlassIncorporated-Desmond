# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Unit tests for the XENOLITH substrate: identity, registry, bus, telemetry."""

from __future__ import annotations

import time

import pytest

from xenolith.bus import Event, EventBus
from xenolith.constants import Domain, RiskTier, canonical
from xenolith.identity import IdentityAuthority, IdentityError
from xenolith.memory import MemoryAccessError, MemoryFabric
from xenolith.registry import AgentRegistry, AgentStatus, RegistryError
from xenolith.telemetry import AnomalyDetector, AuditLedger, MetricSink


# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #
class TestRiskTier:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0, RiskTier.LOW),
            (29, RiskTier.LOW),
            (30, RiskTier.MEDIUM),
            (59, RiskTier.MEDIUM),
            (60, RiskTier.HIGH),
            (84, RiskTier.HIGH),
            (85, RiskTier.CRITICAL),
            (100, RiskTier.CRITICAL),
        ],
    )
    def test_boundaries_match_the_commerce_ladder(self, score, expected):
        assert RiskTier.from_score(score) is expected

    def test_high_and_critical_block_until_approved(self):
        assert RiskTier.HIGH.blocks_until_approved
        assert RiskTier.CRITICAL.blocks_until_approved
        assert not RiskTier.MEDIUM.blocks_until_approved
        assert RiskTier.MEDIUM.requires_approval
        assert not RiskTier.LOW.requires_approval

    def test_canonical_is_key_order_independent(self):
        assert canonical({"a": 1, "b": 2}) == canonical({"b": 2, "a": 1})
        assert canonical({"a": 1}) != canonical({"a": 2})


# --------------------------------------------------------------------------- #
# identity
# --------------------------------------------------------------------------- #
class TestIdentityAuthority:
    def test_issue_requires_a_human_sponsor(self):
        authority = IdentityAuthority()
        with pytest.raises(IdentityError):
            authority.issue("ORPHAN", "")

    def test_issue_is_unique_per_codename(self):
        authority = IdentityAuthority()
        authority.issue("ORACLE", "ops")
        with pytest.raises(IdentityError):
            authority.issue("ORACLE", "ops")

    def test_credential_exposes_no_key_material(self):
        authority = IdentityAuthority()
        credential = authority.issue("ORACLE", "ops")
        rendered = str(credential.as_dict())
        assert credential.fingerprint in rendered
        assert "secret" not in rendered.lower()

    def test_sign_and_verify_roundtrip(self):
        authority = IdentityAuthority()
        authority.issue("ORACLE", "ops")
        envelope = authority.sign("ORACLE", {"action": "intel.read"})
        assert authority.verify(envelope)

    def test_nonce_is_burned_so_replay_fails(self):
        authority = IdentityAuthority()
        authority.issue("ORACLE", "ops")
        envelope = authority.sign("ORACLE", {"action": "intel.read"})
        assert authority.verify(envelope)
        assert not authority.verify(envelope), "replayed envelope must be rejected"

    def test_verify_without_burn_leaves_the_nonce_usable(self):
        authority = IdentityAuthority()
        authority.issue("ORACLE", "ops")
        envelope = authority.sign("ORACLE", {"action": "intel.read"})
        assert authority.verify(envelope, burn=False)
        assert authority.verify(envelope)

    def test_tampered_payload_fails_verification(self):
        from dataclasses import replace

        authority = IdentityAuthority()
        authority.issue("ORACLE", "ops")
        envelope = authority.sign("ORACLE", {"amount": 10})
        forged = replace(envelope, payload={"amount": 10_000})
        assert not authority.verify(forged)

    def test_expired_envelope_is_rejected(self):
        from dataclasses import replace

        authority = IdentityAuthority(envelope_ttl=1)
        authority.issue("ORACLE", "ops")
        envelope = authority.sign("ORACLE", {"action": "intel.read"})
        stale = replace(envelope, issued_at=time.time() - 60)
        assert not authority.verify(stale)

    def test_revocation_stops_signing_and_verification(self):
        authority = IdentityAuthority()
        authority.issue("ORACLE", "ops")
        envelope = authority.sign("ORACLE", {"action": "intel.read"})
        authority.revoke("ORACLE")
        assert not authority.verify(envelope)
        with pytest.raises(IdentityError):
            authority.sign("ORACLE", {"action": "intel.read"})

    def test_revoked_codename_cannot_be_reissued(self):
        authority = IdentityAuthority()
        authority.issue("ORACLE", "ops")
        authority.revoke("ORACLE")
        with pytest.raises(IdentityError):
            authority.issue("ORACLE", "ops")

    def test_agents_cannot_sign_for_each_other(self):
        from dataclasses import replace

        authority = IdentityAuthority()
        authority.issue("ORACLE", "ops")
        authority.issue("BASTION", "ops")
        envelope = authority.sign("BASTION", {"action": "cyber.contain"})
        impersonated = replace(envelope, codename="ORACLE")
        assert not authority.verify(impersonated)

    def test_separate_authorities_do_not_share_keys(self):
        left, right = IdentityAuthority(), IdentityAuthority()
        left.issue("ORACLE", "ops")
        right.issue("ORACLE", "ops")
        envelope = left.sign("ORACLE", {"action": "intel.read"})
        assert not right.verify(envelope)


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #
@pytest.fixture()
def registry() -> AgentRegistry:
    reg = AgentRegistry()
    reg.register(
        "BASTION",
        Domain.CYBERSECURITY,
        "containment",
        "respond to intrusions",
        permissions=["cyber.respond", "intel.read"],
    )
    reg.activate("BASTION")
    return reg


class TestAgentRegistry:
    def test_codenames_are_unique(self, registry):
        with pytest.raises(RegistryError):
            registry.register("BASTION", Domain.OPERATIONS, "r", "s")

    def test_default_partition_is_domain_scoped(self, registry):
        assert registry.get("BASTION").memory_partition == "cybersecurity/BASTION"

    def test_only_active_agents_hold_permissions(self, registry):
        assert registry.has_permission("BASTION", "cyber.respond")
        registry.quarantine("BASTION", reason="anomalous egress")
        assert not registry.has_permission("BASTION", "cyber.respond")

    def test_wildcard_grants_match_by_segment(self):
        reg = AgentRegistry()
        reg.register("PRISM", Domain.INTELLIGENCE, "r", "s", permissions=["intel.*"])
        reg.activate("PRISM")
        assert reg.has_permission("PRISM", "intel.read")
        assert reg.has_permission("PRISM", "intel.deep.read")
        assert not reg.has_permission("PRISM", "cyber.respond")

    def test_wildcard_does_not_match_a_string_prefix(self):
        reg = AgentRegistry()
        reg.register("PRISM", Domain.INTELLIGENCE, "r", "s", permissions=["intel.*"])
        reg.activate("PRISM")
        assert not reg.has_permission("PRISM", "intelligence.read")

    def test_root_wildcard_grants_everything(self):
        reg = AgentRegistry()
        reg.register("PRIME", Domain.EXECUTIVE, "r", "s", permissions=["*"])
        reg.activate("PRIME")
        assert reg.has_permission("PRIME", "policy.administer")

    def test_stale_heartbeat_demotes_to_degraded(self, registry):
        record = registry.get("BASTION")
        record.last_heartbeat = time.time() - 10_000
        assert registry.sweep() == ("BASTION",)
        assert record.status is AgentStatus.DEGRADED

    def test_heartbeat_recovers_a_degraded_agent(self, registry):
        registry.get("BASTION").last_heartbeat = time.time() - 10_000
        registry.sweep()
        registry.heartbeat("BASTION", health=0.9)
        assert registry.get("BASTION").status is AgentStatus.ACTIVE

    def test_retired_agents_cannot_be_reactivated(self, registry):
        registry.retire("BASTION")
        with pytest.raises(RegistryError):
            registry.activate("BASTION")

    def test_quarantine_requires_a_reason(self, registry):
        with pytest.raises(ValueError):
            registry.quarantine("BASTION", reason="  ")


class TestDelegation:
    def test_sub_agent_cannot_exceed_its_parent(self, registry):
        with pytest.raises(RegistryError):
            registry.spawn("BASTION", "BASTION-1", "sub", "scope", permissions=["policy.administer"])

    def test_sub_agent_inherits_domain_and_partition(self, registry):
        child = registry.spawn("BASTION", "BASTION-1", "sub", "scope", permissions=["intel.read"])
        assert child.domain is Domain.CYBERSECURITY
        assert child.memory_partition == "cybersecurity/BASTION/BASTION-1"
        assert child.parent == "BASTION"
        assert "BASTION-1" in registry.get("BASTION").spawned

    def test_only_active_parents_may_spawn(self, registry):
        registry.quarantine("BASTION", reason="under review")
        with pytest.raises(RegistryError):
            registry.spawn("BASTION", "BASTION-2", "sub", "scope")

    def test_wildcard_parent_can_delegate_within_its_scope(self):
        reg = AgentRegistry()
        reg.register("CATALYST", Domain.AUTONOMY, "r", "s", permissions=["intel.*"])
        reg.activate("CATALYST")
        child = reg.spawn("CATALYST", "CATALYST-1", "sub", "scope", permissions=["intel.read"])
        assert "intel.read" in child.permissions


# --------------------------------------------------------------------------- #
# bus
# --------------------------------------------------------------------------- #
class TestEventBus:
    def test_events_are_totally_ordered(self):
        bus = EventBus()
        first = bus.emit("a.b", source="x")
        second = bus.emit("a.c", source="x")
        assert (first.seq, second.seq) == (1, 2)

    def test_duplicate_event_id_is_dropped(self):
        bus = EventBus()
        event = Event(type="a.b", source="x", event_id="fixed")
        assert bus.publish(event) is not None
        assert bus.publish(event) is None
        assert bus.sequence == 1

    def test_wildcard_subscription_matches_by_segment(self):
        bus = EventBus()
        seen: list[str] = []
        bus.subscribe("threat.*", lambda e: seen.append(e.type))
        bus.emit("threat.ioc.observed", source="x")
        bus.emit("cyber.contain", source="x")
        assert seen == ["threat.ioc.observed"]

    def test_root_wildcard_sees_everything(self):
        bus = EventBus()
        seen: list[str] = []
        bus.subscribe("*", lambda e: seen.append(e.type))
        bus.emit("a", source="x")
        bus.emit("b.c", source="x")
        assert seen == ["a", "b.c"]

    def test_failing_handler_is_dead_lettered_not_raised(self):
        bus = EventBus()
        delivered: list[str] = []

        def boom(_event):
            raise RuntimeError("handler exploded")

        bus.subscribe("*", boom)
        bus.subscribe("*", lambda e: delivered.append(e.type))
        bus.emit("a.b", source="x")

        assert delivered == ["a.b"], "a sibling handler must still receive the event"
        assert len(bus.dead_letters) == 1
        assert "handler exploded" in bus.dead_letters[0].error

    def test_unsubscribe_stops_delivery(self):
        bus = EventBus()
        seen: list[str] = []
        cancel = bus.subscribe("*", lambda e: seen.append(e.type))
        bus.emit("a", source="x")
        cancel()
        bus.emit("b", source="x")
        assert seen == ["a"]

    def test_replay_from_a_sequence_number(self):
        bus = EventBus()
        bus.emit("a", source="x")
        marker = bus.sequence
        bus.emit("b", source="x")
        assert [e.type for e in bus.replay(since_seq=marker)] == ["b"]

    def test_trace_reassembles_one_causal_chain(self):
        bus = EventBus()
        bus.emit("a", source="x", trace_id="t1")
        bus.emit("b", source="x", trace_id="t2")
        bus.emit("c", source="x", trace_id="t1")
        assert [e.type for e in bus.trace("t1")] == ["a", "c"]

    def test_source_is_required(self):
        from xenolith.bus import BusError

        bus = EventBus()
        with pytest.raises(BusError):
            bus.publish(Event(type="a", source=" "))


# --------------------------------------------------------------------------- #
# telemetry
# --------------------------------------------------------------------------- #
class TestAuditLedger:
    def test_chain_verifies_when_untouched(self):
        ledger = AuditLedger()
        for i in range(5):
            ledger.record(actor="a", action="act", detail={"i": i})
        assert ledger.verify()

    def test_each_entry_commits_to_its_predecessor(self):
        ledger = AuditLedger()
        first = ledger.record(actor="a", action="one")
        second = ledger.record(actor="a", action="two")
        assert second.prev_hash == first.entry_hash

    def test_mutating_an_entry_breaks_the_chain(self):
        ledger = AuditLedger()
        ledger.record(actor="a", action="one", detail={"amount": 1})
        ledger.record(actor="a", action="two")
        object.__setattr__(ledger.entries[0], "detail", {"amount": 999})
        assert not ledger.verify()

    def test_removing_an_entry_breaks_the_chain(self):
        ledger = AuditLedger()
        for i in range(4):
            ledger.record(actor="a", action=f"act-{i}")
        del ledger._entries[1]  # noqa: SLF001 - deliberately simulating tampering
        assert not ledger.verify()

    def test_require_intact_raises_on_tampering(self):
        from xenolith.telemetry import LedgerTampering

        ledger = AuditLedger()
        ledger.record(actor="a", action="one")
        object.__setattr__(ledger.entries[0], "actor", "someone-else")
        with pytest.raises(LedgerTampering):
            ledger.require_intact()

    def test_filtering_by_risk_floor(self):
        ledger = AuditLedger()
        ledger.record(actor="a", action="low", risk=RiskTier.LOW)
        ledger.record(actor="a", action="high", risk=RiskTier.HIGH)
        ledger.record(actor="a", action="crit", risk=RiskTier.CRITICAL)
        assert [e.action for e in ledger.by_risk(RiskTier.HIGH)] == ["high", "crit"]


class TestAnomalyDetector:
    def test_flags_a_spike_after_learning_a_baseline(self):
        detector = AnomalyDetector(sensitivity=3.0)
        for value in (10, 11, 9, 10, 12, 10, 11, 9, 10, 11):
            assert detector.observe("egress", value) is None
        anomaly = detector.observe("egress", 500)
        assert anomaly is not None
        assert anomaly.series == "egress"
        assert anomaly.z_score >= 3.0

    def test_stays_quiet_below_the_minimum_sample_count(self):
        detector = AnomalyDetector()
        assert detector.observe("cold", 1) is None
        assert detector.observe("cold", 10_000) is None

    def test_a_spike_does_not_immediately_widen_its_own_band(self):
        detector = AnomalyDetector(sensitivity=3.0)
        for _ in range(12):
            detector.observe("flat", 10)
        first = detector.observe("flat", 90)
        assert first is not None

    def test_metrics_snapshot_reports_counters_and_series(self):
        sink = MetricSink()
        sink.increment("actions", 2)
        sink.gauge("health", 0.9)
        sink.observe("latency", 10)
        sink.observe("latency", 20)
        snap = sink.snapshot()
        assert snap["counters"]["actions"] == 2
        assert snap["gauges"]["health"] == 0.9
        assert snap["series"]["latency"]["mean"] == 15.0


# --------------------------------------------------------------------------- #
# memory
# --------------------------------------------------------------------------- #
class TestMemoryFabric:
    def test_an_agent_can_write_and_read_its_own_partition(self):
        fabric = MemoryFabric()
        fabric.write("intelligence/PRISM", "k", {"v": 1}, author="PRISM")
        record = fabric.read("intelligence/PRISM", "intelligence/PRISM", "k")
        assert record is not None and record.value == {"v": 1}

    def test_cross_partition_writes_are_refused(self):
        fabric = MemoryFabric()
        with pytest.raises(MemoryAccessError):
            fabric.write(
                "intelligence/PRISM", "k", 1, author="PRISM", partition="cybersecurity/BASTION"
            )

    def test_cross_partition_reads_need_an_explicit_grant(self):
        fabric = MemoryFabric()
        fabric.write("cybersecurity/BASTION", "k", 1, author="BASTION")
        with pytest.raises(MemoryAccessError):
            fabric.read("intelligence/PRISM", "cybersecurity/BASTION", "k")
        fabric.grant_read("cybersecurity/BASTION", "intelligence/PRISM")
        assert fabric.read("intelligence/PRISM", "cybersecurity/BASTION", "k") is not None

    def test_a_grant_confers_read_only(self):
        fabric = MemoryFabric()
        fabric.grant_read("cybersecurity/BASTION", "intelligence/PRISM")
        assert not fabric.may_write("intelligence/PRISM", "cybersecurity/BASTION")

    def test_a_parent_sees_into_its_sub_agent_partitions(self):
        fabric = MemoryFabric()
        fabric.write("cybersecurity/BASTION/sub-1", "k", 1, author="BASTION-1")
        assert fabric.read("cybersecurity/BASTION", "cybersecurity/BASTION/sub-1", "k") is not None

    def test_sibling_partitions_with_a_shared_prefix_stay_separate(self):
        fabric = MemoryFabric()
        fabric.write("cybersecurity/BASTIONX", "k", 1, author="BASTIONX")
        with pytest.raises(MemoryAccessError):
            fabric.read("cybersecurity/BASTION", "cybersecurity/BASTIONX", "k")

    def test_expired_records_read_as_absent(self):
        fabric = MemoryFabric()
        fabric.write("ops/PULSE", "k", 1, author="PULSE", ttl=-1)
        assert fabric.read("ops/PULSE", "ops/PULSE", "k") is None

    def test_revoking_a_grant_closes_the_read(self):
        fabric = MemoryFabric()
        fabric.write("cybersecurity/BASTION", "k", 1, author="BASTION")
        fabric.grant_read("cybersecurity/BASTION", "intelligence/PRISM")
        fabric.revoke_read("cybersecurity/BASTION", "intelligence/PRISM")
        with pytest.raises(MemoryAccessError):
            fabric.read("intelligence/PRISM", "cybersecurity/BASTION", "k")
