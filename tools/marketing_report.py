#!/usr/bin/env python3
"""Executive marketing report: what the advertising system can prove today.

It reads the repository and nothing else: the campaign packages
(``tools/campaign_registry.py``), the opportunity, experiment and competitor
registries (``tools/growth_registry.py``), the analytics switch
(``analytics.js``), the lead form's API setting (``revenue-command.html``) and
which pages carry the attribution script and which post to the form relay.

Every stage it cannot see from here is reported as ``NOT VERIFIED`` together
with the place the real figure lives. It never counts traffic, leads or
revenue: those exist only in the analytics provider, the owner's mailbox and
the control plane's ledger (``GET /revenue/cockpit``), and the latest daily
revenue report under ``docs/revenue/daily/`` records what was last verified
there.

    python3 tools/marketing_report.py          # the report
    python3 tools/marketing_report.py --json   # the same, as data

It never publishes, spends, or contacts anyone. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign_registry  # noqa: E402  (sibling tools)
import growth_registry  # noqa: E402

NOT_VERIFIED = "NOT VERIFIED"
ANALYTICS = ROOT / "analytics.js"
LEAD_PAGE = ROOT / "revenue-command.html"
DAILY = ROOT / "docs" / "revenue" / "daily"
DECISIONS = "docs/revenue/revenue-decisions.md"
SKIP_DIRS = {".git", ".next", "node_modules", "vendor"}
#: The live CONFIG object only. The file's header comment shows example
#: settings (provider: "ga4"), which must never read as analytics being on.
_CONFIG = re.compile(r"var CONFIG = \{(.*?)\};", re.DOTALL)
_PROVIDER = re.compile(r'provider:\s*"([^"]*)"')
_LEAD_API = re.compile(r'<meta\s+name="cg-revenue-api"\s+content="([^"]*)"')
_RELAY = re.compile(r'<form[^>]+action="https://formsubmit\.co/')


def _pages() -> list[Path]:
    return [
        p for p in sorted(ROOT.rglob("*.html"))
        if not SKIP_DIRS & set(p.relative_to(ROOT).parts)
    ]


def analytics_provider() -> str:
    """The provider analytics.js is configured with, or "" when it is off."""
    config = _CONFIG.search(ANALYTICS.read_text(encoding="utf-8")) if ANALYTICS.is_file() else None
    match = _PROVIDER.search(config.group(1)) if config else None
    return match.group(1).strip().lower() if match else ""


def lead_api() -> str:
    match = _LEAD_API.search(LEAD_PAGE.read_text(encoding="utf-8")) if LEAD_PAGE.is_file() else None
    return match.group(1).strip() if match else ""


def latest_daily_report() -> str | None:
    reports = sorted(DAILY.glob("20??-??-??.md")) if DAILY.is_dir() else []
    return str(reports[-1].relative_to(ROOT)) if reports else None


def collect() -> dict[str, Any]:
    offers = campaign_registry.sellable_offers()
    campaigns = []
    for _path, c in campaign_registry.load(campaign_registry.CAMPAIGN_DIR):
        issues = campaign_registry.problems(c, offers)
        campaigns.append({
            "id": c.get("id"),
            "code": c.get("campaign_code"),
            "status": str(c.get("approval_status") or "draft").lower(),
            "offer": c.get("offer"),
            "ready_for_approval": not issues,
            "tracked_link": campaign_registry.tracked_url(c) if not issues else None,
            "problems": issues,
            "at_approval": campaign_registry.attestations_missing(c),
            "blockers": c.get("blockers", []),
            "dependencies": c.get("dependencies", []),
            "spend_ceiling_cad": c.get("spend_ceiling_cad"),
        })

    pages = []
    for page in _pages():
        text = page.read_text(encoding="utf-8", errors="replace")
        pages.append((str(page.relative_to(ROOT)), text))
    attributed = sorted(p for p, t in pages if campaign_registry.ATTRIBUTION_SCRIPT in t)
    relay = sorted(p for p, t in pages if _RELAY.search(t))

    registries = {}
    for name, path, key in (
        ("opportunities", growth_registry.OPPORTUNITIES, "opportunities"),
        ("experiments", growth_registry.EXPERIMENTS, "experiments"),
        ("competitors", growth_registry.COMPETITORS, "competitors"),
    ):
        registries[name] = growth_registry._load(path, key)
    experiments = [
        {"id": e.get("id"), **growth_registry.evaluate(e)} for e in registries["experiments"]
    ]

    provider = analytics_provider()
    api = lead_api()
    measured = "ON (" + provider + ")" if provider else "OFF"
    funnel = [
        {"stage": "Attention / engagement", "instrument": "analytics.js page views", "state": measured},
        {"stage": "Intent (offer view, CTA, booking, checkout, contact)",
         "instrument": "analytics.js funnel events", "state": measured},
        {"stage": "Lead (server-side, attributed)", "instrument": "revenue-command.html -> POST /revenue/leads",
         "state": "ON (" + api + ")" if api else "OFF: cg-revenue-api is empty, the form is hidden"},
        {"stage": "Lead (form relay)", "instrument": f"{len(relay)} page(s) post to formsubmit.co",
         "state": f"{NOT_VERIFIED} from the repository: relay activation is decision D11 in {DECISIONS}"},
        {"stage": "Payment / revenue", "instrument": "control-plane ledger, GET /revenue/cockpit (admin)",
         "state": f"{NOT_VERIFIED} from the repository"},
    ]

    blockers = []
    if not provider:
        blockers.append("Analytics is off (analytics.js CONFIG.provider is empty): no visit, CTA, booking "
                        "or checkout step is measured. Choosing a provider is the owner's decision; GA4 "
                        "needs a privacy-policy update, Plausible does not.")
    if not api:
        blockers.append("The attributed lead form is off (revenue-command.html cg-revenue-api is empty), "
                        "so no campaign can reach the control plane's lead -> order -> revenue chain.")
    if relay:
        blockers.append(f"{len(relay)} page(s) send enquiries through formsubmit.co; whether the relay "
                        f"delivers is decision D11 in {DECISIONS}.")
    blockers.append("Stripe Payment Link sales carry no cg_ metadata, so the ledger cannot attribute them "
                    "to a campaign; only the server checkout path does.")
    for c in campaigns:
        for item in c["blockers"]:
            blockers.append(f"{c['id']}: {item}")

    ready = [c for c in campaigns if c["ready_for_approval"]]
    live = [c for c in campaigns if c["status"] in campaign_registry.LIVE_STATUSES]
    actions = []
    if not provider:
        actions.append("Owner: choose an analytics provider in analytics.js (its notes: Plausible is "
                       "cookieless; GA4 sets cookies and needs a privacy-policy update). Every funnel "
                       "event is already wired and stays inert until then.")
    if not api:
        actions.append("Owner: deploy the control plane and set cg-revenue-api, or keep campaigns on pages "
                       "that convert by Calendly, e-Transfer or email (both ready campaigns do).")
    if relay:
        actions.append("Owner: close D11 (activate the form relay) before sending traffic to a page with a form.")
    for c in ready:
        if c["status"] not in campaign_registry.LIVE_STATUSES:
            actions.append(f"Owner: review {c['id']} ({c['code']}) for approval; set its spend ceiling "
                           f"(0 for organic), confirm the proposed success and shutdown thresholds, and "
                           f"record its {len(c['at_approval'])} governance item(s) "
                           f"(python3 tools/campaign_registry.py lists them).")
    if not registries["opportunities"]:
        actions.append("Record observed market signals in data/growth/opportunities.json, each with its "
                       "public source and a dated quote. This environment could not reach the primary "
                       "sources (ontario.ca and cyber.gc.ca are blocked by its egress proxy).")

    return {
        "current_state": {
            "campaigns": len(campaigns),
            "ready_for_approval": len(ready),
            "approved_or_active": len(live),
            "analytics": measured,
            "attributed_lead_form": "ON" if api else "OFF",
            "pages_keeping_campaign_tags": attributed,
            "pages_posting_to_form_relay": relay,
        },
        "verified_signals": [
            f"{len(campaigns)} campaign package(s); {len(ready)} complete enough to approve; "
            f"{len(live)} approved or active.",
            f"{len(attributed)} page(s) keep a campaign's tags until the lead form "
            f"({campaign_registry.ATTRIBUTION_SCRIPT}).",
            f"Analytics: {measured}. Attributed lead form: {'ON' if api else 'OFF'}.",
        ],
        "market_opportunities": registries["opportunities"],
        "competitor_observations": registries["competitors"],
        "campaigns": campaigns,
        "conversion_funnel": funnel,
        "blockers": blockers,
        "experiments": experiments,
        "next_actions": actions,
        "revenue_evidence": {
            "state": NOT_VERIFIED,
            "why": "The repository holds no traffic, lead or payment data.",
            "source_of_truth": "GET /revenue/cockpit (admin) on the control plane",
            "latest_daily_report": latest_daily_report(),
        },
    }


def render(report: dict[str, Any]) -> str:
    state = report["current_state"]
    out = ["# ClearGlass executive marketing report", ""]
    out += ["## CURRENT STATE",
            f"- Campaign packages: {state['campaigns']} ({state['ready_for_approval']} ready for approval, "
            f"{state['approved_or_active']} approved or active)",
            f"- Analytics: {state['analytics']}",
            f"- Attributed lead form: {state['attributed_lead_form']}",
            f"- Pages keeping campaign tags: {len(state['pages_keeping_campaign_tags'])}",
            f"- Pages posting to the form relay: {', '.join(state['pages_posting_to_form_relay']) or 'none'}", ""]
    out += ["## VERIFIED SIGNALS", *[f"- {s}" for s in report["verified_signals"]], ""]
    out += ["## MARKET OPPORTUNITIES"]
    opps = report["market_opportunities"]
    out += [f"- {o.get('id')}: {o.get('problem')} [{o.get('evidence_status')}/{o.get('confidence')}]" for o in opps] \
        or ["- None recorded. No market demand is claimed."]
    comps = report["competitor_observations"]
    out += [f"- Competitor observations: {len(comps)}" + ("" if comps else " (no competitor fact is claimed)"), ""]
    out += ["## ACTIVE CAMPAIGNS"]
    live = [c for c in report["campaigns"] if c["status"] in campaign_registry.LIVE_STATUSES]
    out += [f"- {c['id']} ({c['code']}), ceiling CAD {c['spend_ceiling_cad']}" for c in live] \
        or ["- None. No campaign is approved and no spend is authorized."]
    out += ["", "Packages:"]
    for c in report["campaigns"]:
        verdict = "READY FOR APPROVAL" if c["ready_for_approval"] else "INCOMPLETE"
        out.append(f"- {c['id']} [{c['status']}] {verdict}" + (f": {c['tracked_link']}" if c["tracked_link"] else ""))
    out += ["", "## CONVERSION FUNNEL"]
    out += [f"- {s['stage']}: {s['instrument']}. {s['state']}" for s in report["conversion_funnel"]]
    out += ["", "## BLOCKERS", *[f"- {b}" for b in report["blockers"]], ""]
    out += ["## EXPERIMENTS"]
    out += [f"- {e['id']}: {e['outcome']}" for e in report["experiments"]] or ["- None registered. No winner is claimed."]
    out += ["", "## NEXT ACTIONS", *[f"{n}. {a}" for n, a in enumerate(report["next_actions"], 1)], ""]
    rev = report["revenue_evidence"]
    out += ["## REVENUE EVIDENCE",
            f"- {rev['state']}. {rev['why']}",
            f"- Source of truth: {rev['source_of_truth']}",
            f"- Last verified by hand: {rev['latest_daily_report'] or 'no daily report found'}"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    report = collect()
    print(json.dumps(report, indent=2) if args.json else render(report), end="" if not args.json else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
