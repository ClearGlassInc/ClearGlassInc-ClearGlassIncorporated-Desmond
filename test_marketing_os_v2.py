# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import marketing_os_v2 as engine


def make_packet(**overrides):
    packet = {
        "id": "test-initiative",
        "title": "Ship the AI-readiness assessment lead magnet",
        "owner_bot": "LEADGEN-08",
        "reasoning": "Top organic queries show assessment intent.",
        "evidence": ["memory:seo.keywords", "GA4 organic report 2026-06"],
        "expected_outcome": "Qualified leads from organic search.",
        "success_metric": "qualified leads / month",
        "target": "25 by 2026-09-30",
        "next_action": "Draft the assessment outline.",
        "confidence": 72,
        "scores": {
            "revenue_impact": 80,
            "lead_quality": 70,
            "strategic_fit": 90,
            "speed_to_execute": 60,
            "confidence": 72,
        },
        "risk_tier": "low",
    }
    packet.update(overrides)
    return packet


def empty_memory():
    return {
        section: {key: [] for key in keys}
        for section, keys in engine.MEMORY_SCHEMA.items()
    }


class PriorityScoreTests(unittest.TestCase):
    def test_weights_sum_to_one(self) -> None:
        self.assertAlmostEqual(sum(engine.PRIORITY_WEIGHTS.values()), 1.0)

    def test_weighted_formula(self) -> None:
        score = engine.priority_score(make_packet()["scores"])
        expected = 80 * 0.35 + 70 * 0.25 + 90 * 0.20 + 60 * 0.10 + 72 * 0.10
        self.assertEqual(score, round(expected, 2))

    def test_perfect_scores_yield_100(self) -> None:
        self.assertEqual(
            engine.priority_score({k: 100 for k in engine.PRIORITY_WEIGHTS}), 100.0
        )


class PacketValidationTests(unittest.TestCase):
    def test_complete_packet_has_no_missing_fields(self) -> None:
        self.assertEqual(engine.missing_fields(make_packet()), [])

    def test_missing_fields_are_listed_exactly(self) -> None:
        packet = make_packet()
        del packet["reasoning"]
        del packet["success_metric"]
        missing = engine.missing_fields(packet)
        self.assertIn("reasoning", missing)
        self.assertIn("success_metric", missing)
        self.assertEqual(len(missing), 2)

    def test_out_of_range_score_is_flagged(self) -> None:
        packet = make_packet()
        packet["scores"]["revenue_impact"] = 140
        self.assertIn("scores.revenue_impact", engine.missing_fields(packet))

    def test_unknown_owner_bot_is_flagged(self) -> None:
        missing = engine.missing_fields(make_packet(owner_bot="ROGUE-99"))
        self.assertTrue(any(item.startswith("owner_bot") for item in missing))

    def test_unknown_risk_tier_is_flagged(self) -> None:
        missing = engine.missing_fields(make_packet(risk_tier="whatever"))
        self.assertTrue(any(item.startswith("risk_tier") for item in missing))


class QualityGateTests(unittest.TestCase):
    def test_complete_low_risk_packet_auto_executes(self) -> None:
        evaluation = engine.evaluate(make_packet(), empty_memory())
        self.assertTrue(evaluation.advanced)
        self.assertEqual(evaluation.disposition, "auto_execute_and_log")

    def test_incomplete_packet_stops_and_fails_closed(self) -> None:
        evaluation = engine.evaluate({"id": "incomplete"}, empty_memory())
        self.assertEqual(evaluation.disposition, "stopped_missing_information")
        self.assertEqual(evaluation.priority_score, 0.0)
        # Every downstream gate fails rather than being skipped.
        self.assertTrue(all(not gate.passed for gate in evaluation.gates))

    def test_high_and_critical_tiers_are_blocked(self) -> None:
        for tier in ("high", "critical"):
            evaluation = engine.evaluate(make_packet(risk_tier=tier), empty_memory())
            self.assertEqual(evaluation.disposition, "blocked_pending_approval")

    def test_medium_tier_queues_approval(self) -> None:
        evaluation = engine.evaluate(make_packet(risk_tier="medium"), empty_memory())
        self.assertEqual(evaluation.disposition, "queue_approval")

    def test_no_evidence_fails_evidence_gate(self) -> None:
        evaluation = engine.evaluate(make_packet(evidence=[]), empty_memory())
        self.assertFalse(evaluation.advanced)

    def test_low_confidence_needs_escalation(self) -> None:
        low = engine.evaluate(make_packet(confidence=20), empty_memory())
        self.assertFalse(low.advanced)
        escalated = engine.evaluate(
            make_packet(confidence=20, assumption_escalated=True), empty_memory()
        )
        gate = {g.name: g for g in escalated.gates}["evidence"]
        self.assertTrue(gate.passed)

    def test_banned_language_fails_brand_gate(self) -> None:
        evaluation = engine.evaluate(
            make_packet(title="Our revolutionary solution for SMBs"), empty_memory()
        )
        gate = {g.name: g for g in evaluation.gates}["brand_claims"]
        self.assertFalse(gate.passed)

    def test_unapproved_claim_fails_brand_gate(self) -> None:
        memory = empty_memory()
        evaluation = engine.evaluate(
            make_packet(claims=["Cuts breach response time by 80%"]), memory
        )
        gate = {g.name: g for g in evaluation.gates}["brand_claims"]
        self.assertFalse(gate.passed)

        memory["compliance"]["claims_library"].append(
            {"statement": "Cuts breach response time by 80%"}
        )
        evaluation = engine.evaluate(
            make_packet(claims=["Cuts breach response time by 80%"]), memory
        )
        gate = {g.name: g for g in evaluation.gates}["brand_claims"]
        self.assertTrue(gate.passed)


class RankingTests(unittest.TestCase):
    def test_ranks_highest_score_first(self) -> None:
        weak = make_packet(
            id="weak",
            scores={
                "revenue_impact": 10,
                "lead_quality": 10,
                "strategic_fit": 10,
                "speed_to_execute": 10,
                "confidence": 10,
            },
        )
        strong = make_packet(id="strong")
        ranked = engine.rank_initiatives([weak, strong], empty_memory())
        self.assertEqual([e.packet_id for e in ranked], ["strong", "weak"])


class SharedMemoryTests(unittest.TestCase):
    def test_committed_store_is_valid(self) -> None:
        memory = engine.load_memory()
        self.assertEqual(set(memory), set(engine.MEMORY_SCHEMA))

    def test_unknown_section_fails_closed(self) -> None:
        document = json.loads(
            engine.SHARED_MEMORY_PATH.read_text(encoding="utf-8")
        )
        document["memory"]["shadow_ops"] = {}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shared_memory.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ValueError):
                engine.load_memory(path)

    def test_append_entry_is_append_only(self) -> None:
        document = json.loads(
            engine.SHARED_MEMORY_PATH.read_text(encoding="utf-8")
        )
        original = copy.deepcopy(document)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shared_memory.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            engine.append_entry(
                path,
                "experiments",
                "lessons_learned",
                {"lesson": "Confidence labels prevent assumption drift."},
            )
            updated = json.loads(path.read_text(encoding="utf-8"))
        lessons = updated["memory"]["experiments"]["lessons_learned"]
        self.assertEqual(len(lessons), len(
            original["memory"]["experiments"]["lessons_learned"]) + 1)
        self.assertIn("recorded_at", lessons[-1])
        # Nothing pre-existing was removed or rewritten.
        for section, keys in engine.MEMORY_SCHEMA.items():
            for key in keys:
                if section == "experiments" and key == "lessons_learned":
                    continue
                self.assertEqual(
                    updated["memory"][section][key],
                    original["memory"][section][key],
                )

    def test_append_outside_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shared_memory.json"
            path.write_text(
                engine.SHARED_MEMORY_PATH.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                engine.append_entry(path, "audience", "shadow_list", {})


class SelfCheckTests(unittest.TestCase):
    def test_self_check_passes(self) -> None:
        report = engine.self_check()
        self.assertTrue(report["passed"], report)


if __name__ == "__main__":
    unittest.main()
