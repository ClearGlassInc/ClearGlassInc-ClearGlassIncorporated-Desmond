# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for the advanced Agent OS sub-agents (audit, memory, intelligence,
recovery, learning, executive)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_os.audit import GENESIS, AuditLedger  # noqa: E402
from agent_os.executive import Strategy, choose, priority_queue, rank_strategies  # noqa: E402
from agent_os.intelligence import Claim, aggregate_confidence, cross_reference  # noqa: E402
from agent_os.learning import LearningLog  # noqa: E402
from agent_os.memory import MemoryStore  # noqa: E402
from agent_os.recovery import classify, plan_recovery  # noqa: E402


class TestAudit:
    def test_empty_head_is_genesis(self) -> None:
        assert AuditLedger().head == GENESIS

    def test_append_and_verify(self) -> None:
        led = AuditLedger()
        led.append("x", {"a": 1})
        led.append("y", {"b": 2})
        ok, bad = led.verify()
        assert ok is True and bad is None

    def test_tamper_is_detected(self) -> None:
        led = AuditLedger()
        led.append("x", {"a": 1})
        led.append("y", {"b": 2})
        led.entries[0].payload["a"] = 999  # mutate committed payload
        ok, bad = led.verify()
        assert ok is False and bad == 0

    def test_roundtrip_json(self) -> None:
        led = AuditLedger()
        led.append("x", {"a": 1})
        import json
        restored = AuditLedger.from_entries(json.loads(led.to_json()))
        assert restored.verify()[0] is True
        assert restored.head == led.head


class TestMemory:
    def test_missing_memory_reported_missing(self) -> None:
        store = MemoryStore()
        assert store.retrieve("anything") == []

    def test_relevance_filter_excludes_unrelated(self) -> None:
        store = MemoryStore()
        store.remember("semantic", "the sky is blue", authority=0.9)
        assert store.retrieve("database sharding") == []

    def test_recency_breaks_ties(self) -> None:
        store = MemoryStore()
        store.remember("decision", "deploy uses blue green rollout", authority=0.5)
        store.remember("decision", "deploy uses blue green rollout", authority=0.5)
        top = store.retrieve("deploy blue green", k=1)
        assert top and top[0][0].seq == 1  # newest wins on equal accuracy/authority

    def test_authority_influences_rank(self) -> None:
        store = MemoryStore()
        low = store.remember("semantic", "cache uses redis", authority=0.1)
        high = store.remember("semantic", "cache uses redis", authority=0.9)
        ranked = store.retrieve("cache redis", k=2)
        # newest (high, seq=1) should outrank older low-authority one
        assert ranked[0][0].seq == high.seq
        assert {r[0].seq for r in ranked} == {low.seq, high.seq}


class TestIntelligence:
    def test_single_source_is_capped(self) -> None:
        findings = cross_reference([Claim("e", "v", "only", authority=1.0)])
        assert findings[0].confidence <= 0.5
        assert findings[0].contradicted is False

    def test_agreement_beats_single_source(self) -> None:
        findings = cross_reference([
            Claim("e", "v", "a", authority=0.8),
            Claim("e", "v", "b", authority=0.8),
        ])
        assert findings[0].confidence > 0.5
        assert findings[0].contradicted is False

    def test_contradiction_flagged_and_penalised(self) -> None:
        findings = cross_reference([
            Claim("e", "yes", "a", authority=0.9),
            Claim("e", "no", "b", authority=0.4),
        ])
        f = findings[0]
        assert f.contradicted is True
        assert f.value == "yes"  # higher authority wins
        assert "no" in f.conflicting_values

    def test_aggregate_confidence_is_minimum(self) -> None:
        findings = cross_reference([
            Claim("e1", "v", "a", authority=0.9),
            Claim("e1", "v", "b", authority=0.9),
            Claim("e2", "x", "solo", authority=1.0),
        ])
        agg = aggregate_confidence(findings)
        assert agg == min(f.confidence for f in findings)


class TestRecovery:
    @pytest.mark.parametrize("signal,cause", [
        ("HTTP 403 Forbidden", "permissions"),
        ("ModuleNotFoundError: no module named x", "dependency"),
        ("connection timed out to upstream", "external_service"),
        ("invalid input: schema validation failed", "user_data"),
        ("something totally weird", "logic"),
    ])
    def test_classification(self, signal: str, cause: str) -> None:
        assert classify(signal) == cause

    def test_transient_gets_backoff(self) -> None:
        plan = plan_recovery("connection timed out", max_retries=3, base_delay=2.0)
        assert plan.recoverable is True
        assert plan.retry_delays == (2.0, 4.0, 8.0)

    def test_deterministic_fault_escalates_without_retry(self) -> None:
        plan = plan_recovery("invalid input malformed", max_retries=3)
        assert plan.recoverable is False
        assert plan.retry_delays == ()
        assert plan.escalate is True


class TestLearning:
    def test_metrics_rollup(self) -> None:
        log = LearningLog()
        log.record("a", True, 5)
        log.record("b", False, 3)
        m = log.metrics()
        assert m["count"] == 2.0
        assert m["success_rate"] == 0.5
        assert m["mean_duration_minutes"] == 4.0

    def test_lessons_from_failures_only(self) -> None:
        log = LearningLog()
        log.record("a", True, 5)
        log.record("b", False, 3, note="timeout")
        lessons = log.lessons()
        assert len(lessons) == 1 and "timeout" in lessons[0]

    def test_slow_success_flagged(self) -> None:
        log = LearningLog()
        log.record("slow", True, 20)
        assert log.optimization_opportunities(slow_threshold_minutes=10)


class TestExecutive:
    def test_highest_expected_value_chosen(self) -> None:
        strategies = [
            Strategy("safe", value=100, probability=0.9, cost=10, risk=0.1),
            Strategy("risky", value=200, probability=0.4, cost=10, risk=0.6),
        ]
        best = choose(strategies)
        assert best is not None and best.name == "safe" and best.rank == 1

    def test_ranking_is_ordered(self) -> None:
        ranked = rank_strategies([
            Strategy("a", value=100, probability=0.5, cost=0),
            Strategy("b", value=100, probability=0.9, cost=0),
        ])
        assert [r.name for r in ranked] == ["b", "a"]

    def test_priority_queue_orders_by_weight(self) -> None:
        assert priority_queue([("low", 1.0), ("high", 9.0), ("mid", 5.0)]) == [
            "high", "mid", "low",
        ]

    def test_empty_choose_is_none(self) -> None:
        assert choose([]) is None
