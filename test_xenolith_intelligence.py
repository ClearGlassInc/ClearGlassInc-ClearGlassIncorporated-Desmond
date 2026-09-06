# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for the XENOLITH reasoning layers: knowledge graph, fusion, executive."""

from __future__ import annotations

import time

import pytest

from xenolith.constants import Domain
from xenolith.constellation import CONSTELLATION, build
from xenolith.executive import ExecutiveCore, ExecutiveError, MissionState, TaskSpec
from xenolith.fusion import Connector, FusionEngine, Observation, extract_indicators
from xenolith.graph import GraphError, KnowledgeGraph
from xenolith.policy import PolicyEngine
from xenolith.registry import AgentRegistry


# --------------------------------------------------------------------------- #
# knowledge graph
# --------------------------------------------------------------------------- #
class TestKnowledgeGraph:
    def test_entities_accumulate_labels_across_sightings(self):
        graph = KnowledgeGraph()
        graph.upsert_entity("ip:1.1.1.1", "ipv4", labels={"feed-a"})
        graph.upsert_entity("ip:1.1.1.1", "ipv4", labels={"feed-b"})
        assert graph.entity("ip:1.1.1.1").labels == {"feed-a", "feed-b"}

    def test_asserting_about_an_unseen_subject_creates_it(self):
        graph = KnowledgeGraph()
        graph.assert_fact("actor:x", "role", "broker", source="feed-a")
        assert graph.entity("actor:x").kind == "unknown"

    def test_corroboration_beats_a_single_stronger_source(self):
        graph = KnowledgeGraph()
        graph.assert_fact("a", "p", "v", source="s1", confidence=0.6)
        graph.assert_fact("a", "p", "v", source="s2", confidence=0.6)
        two_weak = graph.confidence("a", "p")

        solo = KnowledgeGraph()
        solo.assert_fact("a", "p", "v", source="s1", confidence=0.8)
        assert two_weak > solo.confidence("a", "p")

    def test_disagreement_discounts_confidence(self):
        agreed = KnowledgeGraph()
        agreed.assert_fact("a", "p", "yes", source="s1", confidence=0.8)

        disputed = KnowledgeGraph()
        disputed.assert_fact("a", "p", "yes", source="s1", confidence=0.8)
        disputed.assert_fact("a", "p", "no", source="s2", confidence=0.7)
        assert disputed.confidence("a", "p") < agreed.confidence("a", "p")

    def test_contradictions_are_surfaced_not_resolved(self):
        graph = KnowledgeGraph()
        graph.assert_fact("a", "state", "clean", source="s1")
        graph.assert_fact("a", "state", "compromised", source="s2")
        contradictions = graph.contradictions()
        assert len(contradictions) == 1
        assert {contradictions[0].left.value, contradictions[0].right.value} == {
            "clean",
            "compromised",
        }

    def test_multivalued_predicates_never_contradict(self):
        graph = KnowledgeGraph()
        graph.assert_fact("a", "observed_by", "s1", source="s1", multivalued=True)
        graph.assert_fact("a", "observed_by", "s2", source="s2", multivalued=True)
        assert graph.contradictions() == ()

    def test_multivalued_values_corroborate_rather_than_compete(self):
        graph = KnowledgeGraph()
        graph.assert_fact("a", "observed_by", "s1", source="s1", confidence=0.6, multivalued=True)
        graph.assert_fact("a", "observed_by", "s2", source="s2", confidence=0.6, multivalued=True)
        assert graph.confidence("a", "observed_by") == pytest.approx(0.84)

    def test_retraction_removes_a_claim_but_keeps_the_record(self):
        graph = KnowledgeGraph()
        first = graph.assert_fact("a", "state", "clean", source="s1")
        graph.assert_fact("a", "state", "compromised", source="s2")
        graph.retract(first.assertion_id)
        assert graph.contradictions() == ()
        assert len(graph.assertions("a", include_retracted=True)) == 2

    def test_retracting_an_unknown_assertion_raises(self):
        with pytest.raises(GraphError):
            KnowledgeGraph().retract("asr-999999")

    def test_confidence_is_zero_for_an_unknown_attribute(self):
        assert KnowledgeGraph().confidence("nobody", "nothing") == 0.0

    def test_confidence_must_be_a_probability(self):
        with pytest.raises(ValueError):
            KnowledgeGraph().assert_fact("a", "p", "v", source="s", confidence=1.4)

    def test_traversal_finds_multi_hop_paths(self):
        graph = KnowledgeGraph()
        graph.relate("a", "talks_to", "b", source="s")
        graph.relate("b", "talks_to", "c", source="s")
        paths = graph.paths("a", depth=2)
        assert ("a", "b", "c") in paths

    def test_traversal_is_cycle_safe(self):
        graph = KnowledgeGraph()
        graph.relate("a", "r", "b", source="s")
        graph.relate("b", "r", "a", source="s")
        assert graph.paths("a", depth=4)  # terminates

    def test_traversal_of_an_unknown_node_raises(self):
        with pytest.raises(GraphError):
            KnowledgeGraph().paths("ghost")


# --------------------------------------------------------------------------- #
# indicator extraction
# --------------------------------------------------------------------------- #
class TestExtraction:
    @pytest.mark.parametrize(
        "text,kind,value",
        [
            ("exploited via CVE-2026-10514 today", "cve", "CVE-2026-10514"),
            ("beacon to 198.51.100.24 observed", "ipv4", "198.51.100.24"),
            ("mail from ops@example.com", "email", "ops@example.com"),
            ("hash " + "a" * 64, "sha256", "a" * 64),
            ("see https://evil.example/payload now", "url", "https://evil.example/payload"),
        ],
    )
    def test_typed_indicators_are_recovered(self, text, kind, value):
        found = {(i.kind, i.value) for i in extract_indicators(text)}
        assert (kind, value) in found

    def test_a_url_is_not_also_reported_as_a_bare_domain(self):
        kinds = {i.kind for i in extract_indicators("go to https://evil.example/x")}
        assert "url" in kinds and "domain" not in kinds

    def test_an_email_is_not_shredded_into_its_domain(self):
        kinds = {i.kind for i in extract_indicators("write to ops@example.com")}
        assert "email" in kinds and "domain" not in kinds

    def test_an_ip_is_not_mistaken_for_a_domain(self):
        kinds = {i.kind for i in extract_indicators("host 203.0.113.9 replied")}
        assert kinds == {"ipv4"}

    def test_empty_text_yields_nothing(self):
        assert extract_indicators("") == ()

    def test_duplicates_collapse(self):
        found = extract_indicators("1.2.3.4 and again 1.2.3.4")
        assert len([i for i in found if i.kind == "ipv4"]) == 1


# --------------------------------------------------------------------------- #
# fusion
# --------------------------------------------------------------------------- #
def _connector(name: str, lines: tuple[str, ...], reliability: float = 0.8) -> Connector:
    base = time.time() - 600
    return Connector(
        name=name,
        reliability=reliability,
        fetch=lambda: [
            Observation(source=name, content=line, ts=base + i * 60)
            for i, line in enumerate(lines)
        ],
    )


class TestFusionEngine:
    def test_shared_indicators_pull_observations_into_one_cluster(self):
        engine = FusionEngine()
        engine.ingest(Observation(source="a", content="traffic to 198.51.100.24 spiked"))
        engine.ingest(Observation(source="b", content="198.51.100.24 is a known broker"))
        assert len(engine.cluster()) == 1

    def test_unrelated_observations_stay_apart(self):
        engine = FusionEngine()
        engine.ingest(Observation(source="a", content="traffic to 198.51.100.24 spiked"))
        engine.ingest(Observation(source="b", content="printer firmware upgrade completed"))
        assert len(engine.cluster()) == 2

    def test_lexical_overlap_clusters_observations_without_indicators(self):
        engine = FusionEngine()
        engine.ingest(Observation(source="a", content="ransomware encrypted the finance share"))
        engine.ingest(Observation(source="b", content="ransomware encrypted finance share files"))
        assert len(engine.cluster()) == 1

    def test_independent_corroboration_raises_confidence(self):
        text = "beacon to 198.51.100.24 every 300 seconds"
        solo = FusionEngine()
        solo.ingest(Observation(source="a", content=text))
        solo.ingest(Observation(source="a", content=text + " again"))

        corroborated = FusionEngine()
        corroborated.ingest(Observation(source="a", content=text))
        corroborated.ingest(Observation(source="b", content=text + " again"))

        assert corroborated.packets()[0].confidence > solo.packets()[0].confidence

    def test_source_reliability_shapes_confidence(self):
        text = "beacon to 198.51.100.24 observed"
        strong = FusionEngine()
        strong.ingest(Observation(source="a", content=text), reliability=0.95)
        weak = FusionEngine()
        weak.ingest(Observation(source="a", content=text), reliability=0.2)
        assert strong.packets()[0].confidence > weak.packets()[0].confidence

    def test_stale_observations_are_discounted(self):
        text = "beacon to 198.51.100.24 observed"
        fresh = FusionEngine()
        fresh.ingest(Observation(source="a", content=text, ts=time.time()))
        old = FusionEngine()
        old.ingest(Observation(source="a", content=text, ts=time.time() - 30 * 86400))
        assert old.packets()[0].confidence < fresh.packets()[0].confidence

    def test_ingest_promotes_indicators_into_the_graph(self):
        engine = FusionEngine()
        engine.ingest(Observation(source="a", content="CVE-2026-10514 on 198.51.100.24"))
        ids = {e.entity_id for e in engine.graph.entities()}
        assert "ipv4:198.51.100.24" in ids and "cve:cve-2026-10514" in ids

    def test_co_occurring_indicators_become_graph_edges(self):
        engine = FusionEngine()
        engine.ingest(Observation(source="a", content="CVE-2026-10514 on 198.51.100.24"))
        edges = engine.graph.neighbors("ipv4:198.51.100.24", kind="co_observed")
        assert edges, "indicators named together must be related"

    def test_a_broken_connector_is_isolated_not_fatal(self):
        engine = FusionEngine()

        def explode():
            raise RuntimeError("feed offline")

        engine.register_connector(Connector(name="broken", fetch=explode))
        engine.register_connector(_connector("working", ("198.51.100.24 seen",)))
        collected = engine.collect()

        assert len(collected) == 1
        assert engine.failures and "feed offline" in engine.failures[0]["error"]

    def test_connector_names_are_unique(self):
        engine = FusionEngine()
        engine.register_connector(_connector("dup", ("x",)))
        with pytest.raises(Exception):
            engine.register_connector(_connector("dup", ("y",)))

    def test_reliability_must_be_a_probability(self):
        with pytest.raises(ValueError):
            Connector(name="bad", fetch=lambda: [], reliability=2.0)

    def test_packets_are_ranked_and_filterable(self):
        engine = FusionEngine()
        engine.ingest(Observation(source="a", content="198.51.100.24 beaconing"))
        engine.ingest(Observation(source="b", content="198.51.100.24 confirmed hostile"))
        engine.ingest(Observation(source="c", content="unrelated printer notice"))
        packets = engine.packets()
        assert packets[0].confidence >= packets[-1].confidence
        assert len(engine.packets(minimum_confidence=0.99)) < len(packets)

    def test_packet_timelines_are_chronological(self):
        engine = FusionEngine()
        now = time.time()
        engine.ingest(Observation(source="a", content="198.51.100.24 later", ts=now))
        engine.ingest(Observation(source="b", content="198.51.100.24 earlier", ts=now - 500))
        timeline = engine.packets()[0].timeline
        assert timeline[0]["ts"] < timeline[1]["ts"]

    def test_observations_require_a_source(self):
        from xenolith.fusion import FusionError

        with pytest.raises(FusionError):
            FusionEngine().ingest(Observation(source="  ", content="x"))


# --------------------------------------------------------------------------- #
# executive
# --------------------------------------------------------------------------- #
@pytest.fixture()
def executive() -> ExecutiveCore:
    registry = AgentRegistry()
    registry.register(
        "BASTION", Domain.CYBERSECURITY, "containment", "respond", permissions=["cyber.respond"]
    )
    registry.activate("BASTION")
    registry.heartbeat("BASTION", health=0.95)
    return ExecutiveCore(policy=PolicyEngine(registry=registry), registry=registry)


class TestExecutiveCore:
    def test_objective_value_is_bounded(self, executive):
        with pytest.raises(ExecutiveError):
            executive.declare("too valuable", value=500)

    def test_an_empty_statement_is_refused(self, executive):
        with pytest.raises(ExecutiveError):
            executive.declare("   ", value=50)

    def test_a_passed_deadline_is_maximally_urgent(self, executive):
        objective = executive.declare("overdue", value=50, deadline=time.time() - 10)
        assert objective.urgency() == 1.0

    def test_no_deadline_does_not_mean_maximum_urgency(self, executive):
        undated = executive.declare("someday", value=50)
        due = executive.declare("today", value=50, deadline=time.time() + 60)
        assert undated.urgency() < due.urgency()

    def test_planning_against_an_unknown_action_fails_at_plan_time(self, executive):
        objective = executive.declare("do a thing", value=50)
        with pytest.raises(ExecutiveError):
            executive.plan(
                objective,
                [TaskSpec(action="not.a.real.action", domain=Domain.CYBERSECURITY, summary="x")],
            )

    def test_a_mission_needs_at_least_one_task(self, executive):
        with pytest.raises(ExecutiveError):
            executive.plan(executive.declare("empty", value=10), [])

    def test_tasks_are_ordered_by_computed_priority(self, executive):
        objective = executive.declare("contain", value=90, deadline=time.time() + 3600)
        mission = executive.plan(
            objective,
            [
                TaskSpec(action="cyber.contain", domain=Domain.CYBERSECURITY, summary="isolate"),
                TaskSpec(action="intel.read", domain=Domain.CYBERSECURITY, summary="read"),
            ],
        )
        priorities = [t.priority for t in mission.tasks]
        assert priorities == sorted(priorities, reverse=True)

    def test_high_value_objectives_outrank_low_value_ones(self, executive):
        spec = [TaskSpec(action="intel.read", domain=Domain.CYBERSECURITY, summary="read")]
        high = executive.plan(executive.declare("critical", value=95), spec)
        low = executive.plan(executive.declare("trivial", value=5), spec)
        assert high.tasks[0].priority > low.tasks[0].priority

    def test_work_assigned_to_an_unhealthy_agent_sinks(self, executive):
        spec = [
            TaskSpec(
                action="intel.read",
                domain=Domain.CYBERSECURITY,
                summary="read",
                assigned_to="BASTION",
            )
        ]
        healthy = executive.plan(executive.declare("a", value=60), spec).tasks[0].priority
        executive._registry.heartbeat("BASTION", health=0.05)  # noqa: SLF001
        sick = executive.plan(executive.declare("b", value=60), spec).tasks[0].priority
        assert sick < healthy

    def test_commit_requires_a_named_commander(self, executive):
        mission = executive.plan(
            executive.declare("go", value=50),
            [TaskSpec(action="intel.read", domain=Domain.CYBERSECURITY, summary="read")],
        )
        with pytest.raises(ExecutiveError):
            executive.commit(mission, "  ")
        assert executive.commit(mission, "commander").state is MissionState.COMMITTED

    def test_a_mission_cannot_be_committed_twice(self, executive):
        mission = executive.plan(
            executive.declare("go", value=50),
            [TaskSpec(action="intel.read", domain=Domain.CYBERSECURITY, summary="read")],
        )
        executive.commit(mission, "commander")
        with pytest.raises(ExecutiveError):
            executive.commit(mission, "commander")

    def test_a_fully_blocked_mission_reports_blocked(self, executive):
        mission = executive.plan(
            executive.declare("go", value=50),
            [TaskSpec(action="intel.read", domain=Domain.CYBERSECURITY, summary="read")],
        )
        executive.block(mission, mission.tasks[0].task_id, reason="awaiting authority")
        assert mission.state is MissionState.BLOCKED

    def test_completing_every_task_completes_the_mission(self, executive):
        mission = executive.plan(
            executive.declare("go", value=50),
            [
                TaskSpec(action="intel.read", domain=Domain.CYBERSECURITY, summary="one"),
                TaskSpec(action="telemetry.read", domain=Domain.CYBERSECURITY, summary="two"),
            ],
        )
        for task in list(mission.tasks):
            executive.complete(mission, task.task_id)
        assert mission.state is MissionState.COMPLETE

    def test_brief_flags_work_awaiting_authority(self, executive):
        executive.plan(
            executive.declare("contain", value=90),
            [TaskSpec(action="cyber.contain", domain=Domain.CYBERSECURITY, summary="isolate")],
        )
        brief = executive.brief()
        assert brief["tasks_requiring_authority"] == 1
        assert brief["posture"] == "awaiting-authority"

    def test_brief_reports_nominal_when_nothing_is_pending(self, executive):
        executive.plan(
            executive.declare("read", value=20),
            [TaskSpec(action="intel.read", domain=Domain.CYBERSECURITY, summary="read")],
        )
        assert executive.brief()["posture"] == "nominal"


# --------------------------------------------------------------------------- #
# reference constellation
# --------------------------------------------------------------------------- #
class TestConstellation:
    def test_every_declared_agent_is_enlisted_and_active(self):
        lattice = build(seed_traffic=False)
        assert len(lattice.registry) == len(CONSTELLATION)
        assert all(a.status.can_act for a in lattice.registry.all())

    def test_every_agent_holds_a_credential(self):
        lattice = build(seed_traffic=False)
        for record in lattice.registry.all():
            assert lattice.identity.is_active(record.codename)
            assert record.key_fingerprint

    def test_all_six_domains_are_populated(self):
        health = build(seed_traffic=False).domain_health()
        assert all(health[d.value]["population"] > 0 for d in Domain)

    def test_seeded_traffic_produces_intelligence_and_a_queue(self):
        lattice = build()
        assert lattice.fusion.snapshot()["packets"] > 0
        assert lattice.policy.pending(), "a high-risk action must be waiting on a human"

    def test_the_seeded_containment_did_not_execute(self):
        lattice = build()
        contained = [
            e for e in lattice.ledger.entries if e.action == "cyber.contain" and e.detail["executed"]
        ]
        assert not contained, "containment must not run before approval"

    def test_the_seeded_lattice_is_fail_closed(self):
        state = build().state()
        assert state["governance"]["fail_closed"] is True
        assert state["telemetry"]["ledger_intact"] is True

    def test_the_egress_anomaly_is_detected(self):
        lattice = build()
        series = {a["series"] for a in lattice.anomalies.snapshot()["anomalies"]}
        assert "auth.failures" in series

    def test_writes_stay_inside_their_partition(self):
        lattice = build()
        assert all(r.partition.startswith("intelligence/MERIDIAN") for r in lattice.memory)

    def test_the_executive_may_read_across_domains(self):
        lattice = build()
        assert lattice.memory.may_read("executive/ORACLE", "intelligence/MERIDIAN")
        assert not lattice.memory.may_read("operations/PULSE", "intelligence/MERIDIAN")

    def test_the_build_is_deterministic_in_shape(self):
        first, second = build().state(), build().state()
        assert first["registry"]["population"] == second["registry"]["population"]
        assert first["fusion"]["packets"] == second["fusion"]["packets"]
        assert first["graph"]["entities"] == second["graph"]["entities"]
