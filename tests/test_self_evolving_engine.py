# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import json
import tempfile
import unittest
from pathlib import Path

from bots import self_evolving_engine as se


def _runs(bot_id: str, statuses: list[str], duration: float = 1.0) -> list[dict]:
    return [{"bot": bot_id, "status": s, "duration_s": duration} for s in statuses]


class ScoreFleetTests(unittest.TestCase):
    def test_reliable_priority_bot_ranks_first(self) -> None:
        log = _runs("wealth_ladder", ["ok"] * 5) + _runs("flaky", ["error"] * 5)
        scores = se.score_fleet(log)
        self.assertEqual(scores[0].bot_id, "wealth_ladder")
        self.assertEqual(scores[0].success_rate, 1.0)
        self.assertGreater(scores[0].alignment, 0.0)

    def test_success_rate_uses_recent_window(self) -> None:
        # 30 runs, last 20 all ok → success rate should reflect the window only.
        log = _runs("b", ["error"] * 10 + ["ok"] * 20)
        scores = se.score_fleet(log)
        self.assertEqual(scores[0].runs, se.RECENT_WINDOW)
        self.assertEqual(scores[0].success_rate, 1.0)

    def test_empty_log_yields_no_scores(self) -> None:
        self.assertEqual(se.score_fleet([]), [])


class EvolveTests(unittest.TestCase):
    def test_generation_increments(self) -> None:
        genome = se.Genome(generation=4)
        proposal = se.evolve(genome, se.score_fleet(_runs("b", ["ok"] * 5)))
        self.assertEqual(genome.generation, 5)
        self.assertEqual(proposal["generation"], 5)

    def test_reliable_bot_gets_promoted_weight(self) -> None:
        genome = se.Genome()
        se.evolve(genome, se.score_fleet(_runs("wealth_ladder", ["ok"] * 5)))
        self.assertGreater(genome.weights["wealth_ladder"], 1.0)

    def test_failing_bot_demoted_and_proposed_for_quarantine(self) -> None:
        genome = se.Genome()
        proposal = se.evolve(genome, se.score_fleet(_runs("flaky", ["error"] * 5)))
        self.assertLess(genome.weights["flaky"], 1.0)
        self.assertTrue(proposal["requires_human_approval"])
        self.assertTrue(any("QUARANTINE flaky" in c for c in proposal["proposed_change_set"]))

    def test_quarantine_never_auto_applied(self) -> None:
        genome = se.Genome()
        se.evolve(genome, se.score_fleet(_runs("flaky", ["error"] * 5)))
        # Structural change must NOT mutate the genome's quarantine list.
        self.assertEqual(genome.quarantine, [])

    def test_weights_stay_within_bounds(self) -> None:
        genome = se.Genome(weights={"wealth_ladder": se.WEIGHT_CAP})
        se.evolve(genome, se.score_fleet(_runs("wealth_ladder", ["ok"] * 5)))
        self.assertLessEqual(genome.weights["wealth_ladder"], se.WEIGHT_CAP)

    def test_lineage_records_each_generation(self) -> None:
        genome = se.Genome()
        se.evolve(genome, se.score_fleet(_runs("b", ["ok"] * 5)))
        se.evolve(genome, se.score_fleet(_runs("b", ["ok"] * 5)))
        self.assertEqual(len(genome.lineage), 2)
        self.assertEqual(genome.lineage[-1]["generation"], 2)


class PersistenceTests(unittest.TestCase):
    def test_genome_round_trips_and_inherits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "genome.json"
            g1 = se.Genome(generation=2, weights={"b": 1.5})
            path.write_text(json.dumps(se.asdict(g1)), encoding="utf-8")
            loaded = se.load_genome(path)
            self.assertEqual(loaded.generation, 2)
            self.assertEqual(loaded.weights["b"], 1.5)

    def test_corrupt_genome_falls_back_to_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "genome.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(se.load_genome(path).generation, 0)


if __name__ == "__main__":
    unittest.main()
