"""Opportunities and experiments are held to the evidence they have.

``tools/growth_registry.py`` enforces two rules the growth system stated but
never checked: a hypothesis is not market demand, and an experiment has no
winner until the minimum evidence it set in advance is met and the difference
is significant. These also pin the statistics against known values.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("growth_registry", ROOT / "tools" / "growth_registry.py")
growth = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(growth)  # type: ignore[union-attr]

OFFERS = growth.sellable_offers()

OBSERVED = {
    "id": "opp-1",
    "market": "Ontario",
    "industry": "professional services",
    "problem": "Unmanaged Microsoft 365 admin accounts",
    "buyer": "Managing partner",
    "signal": "Public advisory on M365 account takeover",
    "source": "https://www.cyber.gc.ca/en",
    "observed_at": "2026-09-20",
    "evidence": "Advisory text quoted in the research note",
    "offer": "risk-audit-90",
    "cta": "Book a risk review",
    "funnel_stage": "consideration",
    "confidence": "medium",
    "next_action": "Draft one LinkedIn post for approval",
    "evidence_status": "observed",
}


def test_the_committed_registries_are_valid_and_claim_nothing() -> None:
    assert growth.main(["--check"]) == 0
    for path, key in ((growth.OPPORTUNITIES, "opportunities"), (growth.EXPERIMENTS, "experiments")):
        assert json.loads(path.read_text())[key] == []


def test_the_offers_are_the_ones_clearglass_sells() -> None:
    assert {"risk-audit-90", "rapid-website-deployment-diagnostic", "quick-audit"} <= OFFERS


def test_an_observed_opportunity_with_its_evidence_is_valid() -> None:
    assert growth.opportunity_problems(OBSERVED, OFFERS) == []


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"source": ""}, "public source URL"),
        ({"observed_at": "last week"}, "observed_at"),
        ({"evidence": ""}, "evidence itself"),
        ({"evidence_status": "hypothesis", "confidence": "high"}, "a hypothesis is not demand"),
        ({"evidence_status": "hypothesis", "confidence": "medium"}, "a hypothesis is not demand"),
        ({"offer": "enterprise-soc-retainer"}, "not something ClearGlass sells"),
        ({"campaign": "linkedin spring push"}, "is not a CG-"),
        ({"landing_page": "/no-such-page.html"}, "does not exist"),
        ({"confidence": "certain"}, "confidence must be"),
        ({"funnel_stage": "viral"}, "funnel_stage must be"),
        ({"buyer": ""}, "missing buyer"),
    ],
)
def test_an_idea_cannot_pass_as_demand(change, fragment) -> None:
    issues = growth.opportunity_problems({**OBSERVED, **change}, OFFERS)
    assert any(fragment in issue for issue in issues), issues


def test_a_low_confidence_hypothesis_is_allowed() -> None:
    idea = {**OBSERVED, "evidence_status": "hypothesis", "confidence": "low", "source": "", "evidence": ""}
    assert growth.opportunity_problems(idea, OFFERS) == []


# --- experiments ---------------------------------------------------------------------

EXPERIMENT = {
    "id": "exp-1",
    "hypothesis": "Naming the price above the fold raises checkout starts",
    "control": "Price in the offer section",
    "variant": "Price in the hero",
    "metric": "checkout_started / offer_view",
    "minimum_evidence": {"sample_per_arm": 500, "conversions_per_arm": 20},
    "decision_rule": {"alpha": 0.05},
}


def with_results(control, variant, source="first-party analytics_events export 2026-10-01"):
    return {**EXPERIMENT, "results": {
        "source": source,
        "control": {"visitors": control[0], "conversions": control[1]},
        "variant": {"visitors": variant[0], "conversions": variant[1]},
    }}


def test_the_p_value_matches_a_known_value() -> None:
    # 100/1000 vs 130/1000: pooled rate 0.115, z = 2.1027, two-sided p = 0.0355.
    assert growth.two_proportion_p_value(100, 1000, 130, 1000) == pytest.approx(0.0355, abs=5e-4)
    assert growth.two_proportion_p_value(10, 100, 10, 100) == pytest.approx(1.0)


def test_no_results_is_no_data_and_unsourced_results_are_not_verified() -> None:
    assert growth.evaluate(EXPERIMENT)["outcome"] == growth.NO_DATA
    assert growth.evaluate(with_results((1000, 100), (1000, 130), source=""))["outcome"] == growth.NOT_VERIFIED


def test_a_small_sample_never_produces_a_winner() -> None:
    """A huge lift on 40 visitors is still not evidence."""
    verdict = growth.evaluate(with_results((40, 2), (40, 12)))
    assert verdict["outcome"] == growth.INSUFFICIENT


def test_enough_evidence_and_a_significant_difference_names_the_winner() -> None:
    verdict = growth.evaluate(with_results((1000, 100), (1000, 130)))
    assert verdict["outcome"] == growth.WINNER and verdict["winner"] == "variant"


def test_enough_evidence_without_significance_is_no_difference() -> None:
    assert growth.evaluate(with_results((1000, 100), (1000, 110)))["outcome"] == growth.NO_DIFFERENCE


def test_impossible_results_are_refused() -> None:
    assert growth.evaluate(with_results((100, 150), (100, 10)))["outcome"] == growth.NOT_VERIFIED


def test_a_declared_winner_the_evidence_does_not_support_fails() -> None:
    thin = {**with_results((40, 2), (40, 12)), "declared_winner": "variant"}
    assert growth.unsupported_winner(thin, growth.evaluate(thin))
    solid = {**with_results((1000, 100), (1000, 130)), "declared_winner": "variant"}
    assert growth.unsupported_winner(solid, growth.evaluate(solid)) is None


@pytest.mark.parametrize(
    "change",
    [{"minimum_evidence": {}}, {"minimum_evidence": {"sample_per_arm": 0, "conversions_per_arm": 5}},
     {"decision_rule": {"alpha": 0.5}}, {"hypothesis": ""}],
)
def test_minimum_evidence_and_decision_rule_are_required_up_front(change) -> None:
    assert growth.experiment_problems({**EXPERIMENT, **change})


def test_check_fails_on_an_unsupported_winner(tmp_path, monkeypatch, capsys) -> None:
    registry = tmp_path / "experiments.json"
    registry.write_text(json.dumps({"experiments": [{**with_results((40, 2), (40, 12)), "declared_winner": "variant"}]}))
    monkeypatch.setattr(growth, "EXPERIMENTS", registry)
    assert growth.main(["--check"]) == 1
    assert "not supported" in capsys.readouterr().out
