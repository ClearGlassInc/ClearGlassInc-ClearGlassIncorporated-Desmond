#!/usr/bin/env python3
"""Market opportunities and experiments, held to the evidence they actually have.

Three registries, three rules the growth system kept only by convention:

* **An idea is not demand.** ``data/growth/opportunities.json`` records each
  opportunity as ``Observed -> Evidence -> Interpretation -> Opportunity``.
  One without a public source, a date and the evidence itself is a
  ``hypothesis``, and a hypothesis may only ever carry ``low`` confidence.
  Its offer must be one ClearGlass actually sells, and any campaign code and
  landing page must be real (checked with ``tools/campaign_registry.py``).
* **No winner without the evidence set in advance.** Each experiment in
  ``data/growth/experiments.json`` states its hypothesis, control, variant,
  metric, minimum evidence and decision rule *before* results exist. Results
  are evaluated with a two-sided two-proportion z-test, and only when both
  arms meet the minimum sample and conversions. A ``declared_winner`` the
  evidence does not support fails ``--check``.
* **A competitor is described by what it publishes, never copied.** Each
  entry in ``data/growth/competitors.json`` keeps the public fact
  (``observed``), its dated source and a short quote (``evidence``, at most
  280 characters), then the ``interpretation`` and the ``opportunity`` in
  separate fields, so a reader can always tell fact from inference.

It never publishes, spends, or contacts anyone, and it records no results of
its own: results must name their source, or they are ``NOT VERIFIED``.

    python3 tools/growth_registry.py            # report
    python3 tools/growth_registry.py --check    # exit 1 on an invalid entry or an unsupported winner

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign_registry  # noqa: E402  (sibling tool; shares the campaign-code rules)

OPPORTUNITIES = ROOT / "data" / "growth" / "opportunities.json"
EXPERIMENTS = ROOT / "data" / "growth" / "experiments.json"
COMPETITORS = ROOT / "data" / "growth" / "competitors.json"

OPPORTUNITY_REQUIRED = (
    "id", "market", "industry", "problem", "buyer", "signal", "offer", "cta",
    "funnel_stage", "confidence", "next_action", "evidence_status",
)
EVIDENCE_STATUSES = {"hypothesis", "observed"}
CONFIDENCE = {"low", "medium", "high"}
FUNNEL_STAGES = {"awareness", "consideration", "decision", "retention"}
_DATE = re.compile(r"^20\d\d-[01]\d-[0-3]\d$")

EXPERIMENT_REQUIRED = (
    "id", "hypothesis", "control", "variant", "metric", "minimum_evidence", "decision_rule",
)
WINNER = "WINNER"
NO_DIFFERENCE = "NO SIGNIFICANT DIFFERENCE"
INSUFFICIENT = "INSUFFICIENT EVIDENCE"
NOT_VERIFIED = "NOT VERIFIED"
NO_DATA = "NO DATA"


#: One definition of "something ClearGlass sells", shared with the campaign gate.
sellable_offers = campaign_registry.sellable_offers


# --- opportunities ------------------------------------------------------------------


def opportunity_problems(opp: dict[str, Any], offers: set[str]) -> list[str]:
    found = [f"missing {field}" for field in OPPORTUNITY_REQUIRED if not opp.get(field)]
    status = opp.get("evidence_status")
    confidence = opp.get("confidence")
    if status and status not in EVIDENCE_STATUSES:
        found.append(f"evidence_status must be one of {sorted(EVIDENCE_STATUSES)}")
    if confidence and confidence not in CONFIDENCE:
        found.append(f"confidence must be one of {sorted(CONFIDENCE)}")
    if opp.get("funnel_stage") and opp["funnel_stage"] not in FUNNEL_STAGES:
        found.append(f"funnel_stage must be one of {sorted(FUNNEL_STAGES)}")
    if status == "observed":
        source = str(opp.get("source") or "")
        if not source.startswith(("https://", "http://")):
            found.append("an observed opportunity needs a public source URL")
        if not _DATE.match(str(opp.get("observed_at") or "")):
            found.append("an observed opportunity needs observed_at (YYYY-MM-DD)")
        if not opp.get("evidence"):
            found.append("an observed opportunity needs the evidence itself, not only a link")
    if status == "hypothesis" and confidence in {"medium", "high"}:
        found.append("a hypothesis is not demand: its confidence can only be low until evidence is observed")
    if opp.get("offer") and opp["offer"] not in offers:
        found.append(f"offer {opp['offer']!r} is not something ClearGlass sells (price book or service catalogue)")
    if opp.get("campaign") and campaign_registry.parse_code(opp["campaign"]) is None:
        found.append(f"campaign {opp['campaign']!r} is not a CG-<CHANNEL>-<AUDIENCE>-<OFFER>-<YYYY>-Q<n> code")
    if opp.get("landing_page"):
        issue = campaign_registry.destination_problem(opp["landing_page"])
        if issue:
            found.append(issue)
    return found


# --- experiments --------------------------------------------------------------------


def two_proportion_p_value(c1: int, n1: int, c2: int, n2: int) -> float:
    """Two-sided p-value for a difference in conversion rate between two arms."""
    pooled = (c1 + c2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (c2 / n2 - c1 / n1) / se
    return math.erfc(abs(z) / math.sqrt(2))


def experiment_problems(exp: dict[str, Any]) -> list[str]:
    found = [f"missing {field}" for field in EXPERIMENT_REQUIRED if not exp.get(field)]
    minimum = exp.get("minimum_evidence") or {}
    for key in ("sample_per_arm", "conversions_per_arm"):
        if not isinstance(minimum.get(key), int) or minimum.get(key, 0) < 1:
            found.append(f"minimum_evidence.{key} must be a positive integer set before results exist")
    alpha = (exp.get("decision_rule") or {}).get("alpha", 0.05)
    if not isinstance(alpha, int | float) or not 0 < alpha <= 0.1:
        found.append("decision_rule.alpha must be in (0, 0.1]")
    return found


def evaluate(exp: dict[str, Any]) -> dict[str, Any]:
    """What the recorded results support. Never more than that."""
    results = exp.get("results")
    if not results:
        return {"outcome": NO_DATA, "reason": "no results recorded"}
    if not results.get("source"):
        return {"outcome": NOT_VERIFIED, "reason": "results name no source (analytics export, ledger query)"}
    try:
        n1, c1 = int(results["control"]["visitors"]), int(results["control"]["conversions"])
        n2, c2 = int(results["variant"]["visitors"]), int(results["variant"]["conversions"])
    except (KeyError, TypeError, ValueError):
        return {"outcome": NOT_VERIFIED, "reason": "results need visitors and conversions for both arms"}
    if min(n1, n2) < 1 or not (0 <= c1 <= n1 and 0 <= c2 <= n2):
        return {"outcome": NOT_VERIFIED, "reason": "conversions must be between 0 and visitors"}

    minimum = exp.get("minimum_evidence") or {}
    sample, conversions = minimum.get("sample_per_arm", 0), minimum.get("conversions_per_arm", 0)
    rates = {"control": c1 / n1, "variant": c2 / n2}
    if min(n1, n2) < sample or min(c1, c2) < conversions:
        return {
            "outcome": INSUFFICIENT,
            "reason": f"needs {sample} visitors and {conversions} conversions per arm; "
            f"has control {n1}/{c1}, variant {n2}/{c2}",
            "rates": rates,
        }
    alpha = float((exp.get("decision_rule") or {}).get("alpha", 0.05))
    p_value = two_proportion_p_value(c1, n1, c2, n2)
    if p_value >= alpha:
        return {"outcome": NO_DIFFERENCE, "p_value": p_value, "alpha": alpha, "rates": rates}
    winner = "variant" if rates["variant"] > rates["control"] else "control"
    return {"outcome": WINNER, "winner": winner, "p_value": p_value, "alpha": alpha, "rates": rates}


def unsupported_winner(exp: dict[str, Any], verdict: dict[str, Any]) -> str | None:
    declared = exp.get("declared_winner")
    if not declared:
        return None
    if verdict["outcome"] != WINNER or verdict.get("winner") != declared:
        return f"declared_winner {declared!r} is not supported: {verdict['outcome']}"
    return None


# --- competitors --------------------------------------------------------------------

COMPETITOR_REQUIRED = (
    "id", "competitor", "category", "observed", "source", "observed_at", "evidence",
    "interpretation", "opportunity",
)
COMPETITOR_CATEGORIES = {
    "positioning", "services", "pricing", "messaging", "content", "cta",
    "case_study", "advertising", "technology", "segment",
}
#: A quote long enough to support the observation and too short to be a copy.
EVIDENCE_MAX = 280


def competitor_problems(entry: dict[str, Any]) -> list[str]:
    found = [f"missing {field}" for field in COMPETITOR_REQUIRED if not entry.get(field)]
    if entry.get("category") and entry["category"] not in COMPETITOR_CATEGORIES:
        found.append(f"category must be one of {sorted(COMPETITOR_CATEGORIES)}")
    if entry.get("source") and not str(entry["source"]).startswith("https://"):
        found.append("source must be the public https:// page the fact was read on")
    if entry.get("observed_at") and not _DATE.match(str(entry["observed_at"])):
        found.append("observed_at must be YYYY-MM-DD")
    if len(str(entry.get("evidence") or "")) > EVIDENCE_MAX:
        found.append(f"evidence is a quote of at most {EVIDENCE_MAX} characters, not a copy of their content")
    if entry.get("observed") and entry.get("observed") == entry.get("interpretation"):
        found.append("interpretation must say what the fact means, not repeat it")
    return found


# --- CLI ------------------------------------------------------------------------------


def _load(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")).get(key, []))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 on an invalid entry or unsupported winner")
    args = parser.parse_args(argv)

    offers = sellable_offers()
    failures = 0
    opportunities = _load(OPPORTUNITIES, "opportunities")
    print(f"Opportunities: {len(opportunities)} "
          f"({sum(1 for o in opportunities if o.get('evidence_status') == 'observed')} observed, "
          f"{sum(1 for o in opportunities if o.get('evidence_status') == 'hypothesis')} hypothesis)")
    for opp in opportunities:
        issues = opportunity_problems(opp, offers)
        print(f"  {opp.get('id', '?')} [{opp.get('evidence_status', '?')}/{opp.get('confidence', '?')}] "
              f"{'VALID' if not issues else 'INVALID'}")
        for issue in issues:
            print(f"      - {issue}")
        failures += bool(issues)

    experiments = _load(EXPERIMENTS, "experiments")
    print(f"Experiments: {len(experiments)}")
    for exp in experiments:
        issues = experiment_problems(exp)
        verdict = evaluate(exp) if not issues else {"outcome": "INVALID"}
        claim = unsupported_winner(exp, verdict) if not issues else None
        if claim:
            issues.append(claim)
        print(f"  {exp.get('id', '?')}: {verdict['outcome']}"
              + (f" ({verdict.get('winner')}, p={verdict['p_value']:.4f})" if verdict.get("winner") else ""))
        for issue in issues:
            print(f"      - {issue}")
        failures += bool(issues)

    competitors = _load(COMPETITORS, "competitors")
    print(f"Competitor observations: {len(competitors)}")
    for entry in competitors:
        issues = competitor_problems(entry)
        print(f"  {entry.get('id', '?')} [{entry.get('competitor', '?')}/{entry.get('category', '?')}] "
              f"{'VALID' if not issues else 'INVALID'}")
        for issue in issues:
            print(f"      - {issue}")
        failures += bool(issues)

    if not opportunities and not experiments and not competitors:
        print("Nothing recorded yet. No demand, result, winner or competitor fact is claimed.")
    return 1 if args.check and failures else 0


if __name__ == "__main__":
    sys.exit(main())
