#!/usr/bin/env python3
"""ClearGlassInc Artemis strategic viral content engine.

Generates a deterministic weekly content pack for the 2040 dominance framework:
7 concepts x 5 publishing formats plus hashtags, UTM routing, and KPI dashboard JSON.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

BASE_URL = "https://www.clearglassinc.com"

PILLARS = {
    "ai_risk": {
        "name": "AI Risk Enforcement",
        "keyword": "auditable AI systems",
        "path": "/ai-audit-framework",
        "campaign": "pillar_ai_risk",
        "hashtags": ["#AI", "#AIGovernance", "#AuditableAI", "#Cybersecurity", "#Leadership"],
    },
    "cyber_osint": {
        "name": "Cybersecurity & OSINT",
        "keyword": "OSINT for corporate security",
        "path": "/osint-guide",
        "campaign": "pillar_cybersecurity",
        "hashtags": ["#Cybersecurity", "#OSINT", "#ThreatIntel", "#RiskManagement", "#Leadership"],
    },
    "legal_tech": {
        "name": "Legal-Tech Automation",
        "keyword": "contract review automation ROI",
        "path": "/legal-automation",
        "campaign": "pillar_legal_tech",
        "hashtags": ["#LegalTech", "#Automation", "#AI", "#CorporateLaw", "#Operations"],
    },
}

CONCEPTS = [
    ("The AI Lie Nobody Tells You", "ai_risk", "95% of AI projects do not fail because the model is weak. They fail because nobody can audit the decision trail."),
    ("I Built This Cybersecurity Bot in 3 Hours", "cyber_osint", "I built a corporate OSINT triage bot in 3 hours. The hard part was not Python. It was trust boundaries."),
    ("The OSINT Hack That Made My Client $2M", "cyber_osint", "The highest-ROI OSINT move is not secret data. It is public data fused faster than your competitor can explain it."),
    ("Why Most AI Automation Fails (And How I Fixed It)", "ai_risk", "The problem is not AI automation. The problem is automation with no human control plane."),
    ("Legal-Tech Automation Changed My Life", "legal_tech", "A contract review bot that cannot prove ROI is a toy. Legal automation should pay for itself in the first renewal cycle."),
    ("The Future-Proof Tech Stack (2026 Edition)", "ai_risk", "The future-proof stack is not more tools. It is auditable agents, policy-as-code, and rollback-ready workflows."),
    ("I Found My Competitor's $10M Secret", "cyber_osint", "Your competitor's strategy is usually not hidden. It is scattered across hiring, contracts, filings, and timing."),
]

PLATFORMS = ["linkedin", "x", "youtube", "instagram", "site"]


def utm(pillar_key: str, source: str) -> str:
    pillar = PILLARS[pillar_key]
    return f"{BASE_URL}{pillar['path']}?utm_source={source}&utm_campaign={pillar['campaign']}"


@dataclass(frozen=True)
class ContentPack:
    concept_id: int
    title: str
    pillar: str
    keyword: str
    seo_blog_outline: dict[str, Any]
    linkedin_post: str
    x_thread: list[str]
    linkedin_carousel: list[dict[str, str]]
    video_script: list[dict[str, str]]
    hashtags: list[str]
    conversion_urls: dict[str, str]


def seo_outline(title: str, pillar_key: str) -> dict[str, Any]:
    keyword = PILLARS[pillar_key]["keyword"]
    return {
        "target_word_count": 2000,
        "primary_keyword": keyword,
        "h1": title,
        "h2_sections": [
            {"heading": f"Why {keyword} became a board-level requirement", "h3": ["Operational risk", "Auditability gap", "Revenue impact"]},
            {"heading": "The ClearGlassInc Artemis control model", "h3": ["Data lineage", "Human approval gates", "Model routing"]},
            {"heading": "Implementation blueprint", "h3": ["Python services", "Policy-as-code", "Observability"]},
            {"heading": "ROI and executive scorecard", "h3": ["Precision", "Latency", "Trust", "Revenue attribution"]},
        ],
        "faq_schema": [
            {"question": f"What are {keyword}?", "answer": "Systems whose data, prompts, models, tool calls, approvals, and outcomes can be inspected and governed end to end."},
            {"question": "How do you reduce AI operational risk?", "answer": "Use mission-scoped data, evaluated prompts, approval gates, immutable logs, and Apollo-style rollback."},
        ],
        "howto_schema": ["Inventory data sources", "Map ontology and permissions", "Add evals", "Canary workflow changes", "Review metrics weekly"],
    }


def linkedin_post(idx: int, title: str, pillar_key: str, hook: str) -> str:
    return (
        f"{hook}\n\n"
        "Last week at ClearGlassInc Artemis, we treated this like a mission system, not a content slogan: every claim needed lineage, every workflow needed rollback, and every recommendation needed a human approval path.\n\n"
        "The uncomfortable truth: executives do not need another AI demo. They need a system that can explain what it saw, what it ignored, why it recommended action, and who approved the change.\n\n"
        "My operating rule: if an AI workflow cannot be audited under pressure, it is not production AI. It is theater.\n\n"
        f"Download the framework: {utm(pillar_key, 'linkedin')}\n\n"
        "Comment 'ARTEMIS' and I will send the control-plane checklist."
    )


def x_thread(title: str, pillar_key: str, hook: str) -> list[str]:
    url = utm(pillar_key, "x")
    keyword = PILLARS[pillar_key]["keyword"]
    tweets = [
        f"1/ {hook}",
        f"2/ The board-level keyword is '{keyword}' because vague AI promises do not survive audits.",
        "3/ The stack: Foundry ontology + Gotham investigations + AIP agents + Apollo rollback.",
        "4/ Rule: agents can propose. Humans approve anything operationally significant.",
        "5/ Code pattern: policy_check(user, mission, action) before every tool call.",
        "6/ Precision without provenance is fragile. Provenance without latency is unusable.",
        "7/ Capture feedback: accepts, rejects, edits, false positives, missed correlations, outcomes.",
        "8/ Convert feedback into eval cases before changing prompts or workflows.",
        "9/ Canary upgrades at 5%. Roll back on precision, latency, trust, or policy regressions.",
        "10/ Every prompt is a governed artifact: versioned, diffed, tested, signed.",
        "11/ Every recommendation carries evidence, confidence, blast radius, and rollback plan.",
        "12/ This is how AI moves from demo to command system.",
        "13/ The moat is not the model. The moat is the audited operating loop.",
        "14/ Build for machine speed. Govern for human accountability.",
        f"15/ Get the framework: {url}",
    ]
    return tweets


def carousel(title: str, pillar_key: str, hook: str) -> list[dict[str, str]]:
    keyword = PILLARS[pillar_key]["keyword"]
    return [
        {"slide": "1", "headline": title, "visual": "Black glass UI, red alert line, executive dashboard", "copy": hook},
        {"slide": "2", "headline": "The hidden failure", "visual": "Broken workflow diagram", "copy": "Most teams automate before they can audit."},
        {"slide": "3", "headline": "The Artemis control plane", "visual": "Ontology graph + approval gate", "copy": f"Make {keyword} measurable: lineage, confidence, policy, evals."},
        {"slide": "4", "headline": "The safe self-upgrade loop", "visual": "Feedback → eval → canary → rollback", "copy": "AI proposes improvements; humans approve guarded deployments."},
        {"slide": "5", "headline": "Steal the checklist", "visual": "QR/URL CTA", "copy": utm(pillar_key, "linkedin_carousel")},
    ]


def video(title: str, pillar_key: str, hook: str) -> list[dict[str, str]]:
    return [
        {"time": "0-5s", "visual": "Hard cut to alert dashboard", "voiceover": hook},
        {"time": "5-15s", "visual": "Fast Python terminal + ontology graph", "voiceover": "The model is not the system. The control loop is the system."},
        {"time": "15-30s", "visual": "Agent tool call paused at approval gate", "voiceover": "Read-only actions can run. Mutations wait for analysts. External effects need command approval."},
        {"time": "30-45s", "visual": "Eval dashboard comparing prompt versions", "voiceover": "Every operator correction becomes an eval before it becomes a workflow update."},
        {"time": "45-60s", "visual": "CTA screen with ClearGlassInc Artemis", "voiceover": f"Download the framework at {utm(pillar_key, 'youtube')}"},
    ]


def build_pack() -> list[ContentPack]:
    packs: list[ContentPack] = []
    for idx, (title, pillar_key, hook) in enumerate(CONCEPTS, start=1):
        packs.append(ContentPack(
            concept_id=idx,
            title=title,
            pillar=PILLARS[pillar_key]["name"],
            keyword=PILLARS[pillar_key]["keyword"],
            seo_blog_outline=seo_outline(title, pillar_key),
            linkedin_post=linkedin_post(idx, title, pillar_key, hook),
            x_thread=x_thread(title, pillar_key, hook),
            linkedin_carousel=carousel(title, pillar_key, hook),
            video_script=video(title, pillar_key, hook),
            hashtags=PILLARS[pillar_key]["hashtags"],
            conversion_urls={platform: utm(pillar_key, platform) for platform in PLATFORMS},
        ))
    return packs


def dashboard() -> dict[str, Any]:
    return {
        "generated_at": date.today().isoformat(),
        "targets_90_day": {
            "assets_generated": 90,
            "linkedin_engagement_rate": 0.05,
            "x_impressions": 500000,
            "lead_magnet_downloads": 100,
            "ai_answer_box_citations": 3,
            "google_rank_target": 3,
            "time_saved_hours_per_week": 15,
            "revenue_target_low": 250000,
            "revenue_target_high": 1000000,
        },
        "event_schema": ["asset_id", "platform", "utm_source", "impressions", "clicks", "downloads", "qualified_leads", "revenue_attributed"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="content/weekly_content_20260701.json")
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"organization": "ClearGlassInc Artemis", "weekly_pack": [asdict(p) for p in build_pack()], "analytics_dashboard": dashboard()}
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out} with {len(payload['weekly_pack'])} concepts")


if __name__ == "__main__":
    main()
