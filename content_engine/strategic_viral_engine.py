"""ClearGlassInc 2040 dominance content engine.

Deterministically generates a weekly multi-format content pack for the Auditable AI,
OSINT, and legal-tech automation authority flywheel.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

BASE_URL = "https://www.clearglassinc.com"
WEEK_ID = "20260701"

PILLARS = {
    "ai_risk": {
        "name": "AI Risk Enforcement",
        "keyword": "auditable AI systems",
        "path": "/ai-audit-framework",
        "campaign": "pillar_ai_risk",
        "offer": "AI Audit Framework",
        "revenue": "consulting audits ($5K-25K/month) and enterprise AI systems ($50K-200K/project)",
    },
    "cybersecurity": {
        "name": "Cybersecurity & OSINT",
        "keyword": "OSINT for corporate security",
        "path": "/osint-guide",
        "campaign": "pillar_cybersecurity",
        "offer": "OSINT Corporate Security Guide",
        "revenue": "cybersecurity audits ($10K-50K), OSINT training ($500-2K), investigative consulting ($25K-100K)",
    },
    "legal_tech": {
        "name": "Legal-Tech Automation",
        "keyword": "contract review automation ROI",
        "path": "/legal-automation",
        "campaign": "pillar_legal_tech",
        "offer": "Legal Automation ROI Calculator",
        "revenue": "legal automation contracts ($20K-100K), course sales ($500-2K), software tools ($1K-10K)",
    },
}

CONCEPTS = [
    (
        1,
        "The AI Lie Nobody Tells You",
        "ai_risk",
        "95% of AI pilots do not fail because the model is weak. They fail because nobody can audit the decision trail.",
    ),
    (
        2,
        "I Built This Cybersecurity Bot in 3 Hours",
        "cybersecurity",
        "A 3-hour Python bot can surface more corporate exposure than a week of manual spreadsheet OSINT.",
    ),
    (
        3,
        "The OSINT Hack That Made My Client $2M",
        "cybersecurity",
        "The fastest $2M recovery path was not a louder sales team. It was one mapped fraud graph.",
    ),
    (
        4,
        "Why Most AI Automation Fails (And How I Fixed It)",
        "ai_risk",
        "The problem is not AI automation. The problem is automation without enforcement layers.",
    ),
    (
        5,
        "Legal-Tech Automation Changed My Life",
        "legal_tech",
        "Contract review automation ROI becomes obvious when every clause becomes searchable, scored, and routed.",
    ),
    (
        6,
        "The Future-Proof Tech Stack (2026 Edition)",
        "ai_risk",
        "The 2026 stack is not more apps. It is auditable AI, typed workflows, event logs, and human approval gates.",
    ),
    (
        7,
        "I Found My Competitor's $10M Secret",
        "cybersecurity",
        "Most competitive intelligence is hiding in public records, job posts, vendor trails, and exposed infrastructure metadata.",
    ),
]


@dataclass(frozen=True)
class Concept:
    id: int
    title: str
    pillar: str
    hook: str


def utm_url(pillar: dict[str, str], source: str, concept_id: int, medium: str) -> str:
    return f"{BASE_URL}{pillar['path']}?" + urlencode(
        {
            "utm_source": source,
            "utm_medium": medium,
            "utm_campaign": pillar["campaign"],
            "utm_content": f"concept_{concept_id:02d}_{source}",
        }
    )


def seo_outline(concept: Concept, pillar: dict[str, str]) -> dict[str, Any]:
    kw = pillar["keyword"]
    return {
        "target_keyword": kw,
        "meta_title": f"{concept.title}: {kw.title()} Blueprint | ClearGlassInc",
        "meta_description": f"A technical executive guide to {kw}, oversight layers, ROI, auditability, and deployment discipline.",
        "slug": f"/{concept.title.lower().replace(' ', '-').replace('(', '').replace(')', '')}",
        "outline": [
            {
                "h2": f"The executive problem behind {kw}",
                "h3": [
                    "Why hype hides operational risk",
                    "Where budgets leak",
                    "What boards actually need to measure",
                ],
            },
            {
                "h2": "The ClearGlassInc enforcement model",
                "h3": [
                    "Evidence graph",
                    "Human approval gates",
                    "Decision logs",
                    "Rollback plan",
                ],
            },
            {
                "h2": "Implementation architecture",
                "h3": [
                    "Data intake",
                    "Policy checks",
                    "Agent workflow",
                    "Observability dashboard",
                ],
            },
            {
                "h2": "ROI model",
                "h3": [
                    "Cost of manual review",
                    "Cost of false positives",
                    "Payback period",
                    "Enterprise contract path",
                ],
            },
            {
                "h2": "90-day rollout",
                "h3": [
                    "Week 1 baseline",
                    "Weeks 2-4 pilot",
                    "Weeks 5-8 scale",
                    "Weeks 9-12 board report",
                ],
            },
        ],
        "faq_schema": [
            {
                "question": f"What are {kw}?",
                "answer": "Systems with traceable inputs, explainable outputs, approval evidence, and continuous monitoring.",
            },
            {
                "question": "How fast can a pilot launch?",
                "answer": "A focused assessment can start in 48 hours; production rollout depends on data access and controls.",
            },
            {
                "question": "What is the primary risk?",
                "answer": "Unlogged autonomous decisions that cannot be defended during audits, disputes, or incidents.",
            },
        ],
        "howto_schema": [
            "Inventory systems",
            "Map decisions",
            "Add oversight gates",
            "Measure outcomes",
            "Promote approved workflow versions",
        ],
    }


def linkedin_post(concept: Concept, pillar: dict[str, str]) -> str:
    url = utm_url(pillar, "linkedin", concept.id, "social")
    return f"{concept.hook}\n\nLast week at ClearGlassInc, we pressure-tested this exact problem: an impressive automation demo with no audit trail, no rollback story, and no accountable owner. That is not transformation. That is unmanaged operational debt.\n\nThe winning pattern is boring in the best possible way:\n1. Log every input.\n2. Score every output.\n3. Route risky decisions to humans.\n4. Capture corrections.\n5. promote only workflows that survive evals.\n\nThat is how {pillar['keyword']} become a revenue engine instead of a board-level liability.\n\nIf your AI, OSINT, or legal automation stack cannot explain what it did, why it did it, and who approved it, it is not enterprise-grade yet.\n\nDownload the {pillar['offer']}: {url}"


def x_thread(concept: Concept, pillar: dict[str, str]) -> list[str]:
    url = utm_url(pillar, "x", concept.id, "social")
    tweets = [
        f"1/ {concept.hook}",
        "2/ The market rewards speed. Regulators, customers, and courts reward proof. The winner needs both.",
        "3/ My rule at ClearGlassInc: no critical workflow ships unless it creates evidence while it operates.",
        "4/ Evidence means: source, timestamp, model version, prompt version, policy decision, human approval, and outcome.",
        "5/ The hidden failure mode is silent automation drift. Yesterday's perfect prompt becomes tomorrow's liability.",
        "6/ Fix: treat prompts like production code. Version them. Test them. Roll them back.",
        "7/ Python pattern:\n```python\nassert decision.audit_id\nassert decision.policy == 'approved'\nassert decision.confidence >= threshold\n```",
        f"8/ For {pillar['keyword']}, the dashboard should show precision, recall, latency, override rate, and revenue impact.",
        "9/ Operators are not blockers. They are the labeled-data engine that makes the system compound.",
        "10/ Every correction becomes an eval. Every eval becomes a promotion gate. Every promotion gate protects trust.",
        "11/ The goal is not autonomous chaos. The goal is machine speed inside human-approved guardrails.",
        f"12/ Revenue angle: {pillar['revenue']}.",
        "13/ If a vendor cannot show decision lineage, ask what happens during a breach, lawsuit, or failed audit.",
        "14/ Build the audit trail before the incident. After the incident is too late.",
        f"15/ Download the {pillar['offer']}: {url}",
    ]
    return tweets


def carousel(concept: Concept, pillar: dict[str, str]) -> list[dict[str, str]]:
    url = utm_url(pillar, "linkedin", concept.id, "carousel")
    return [
        {
            "slide": "1",
            "headline": concept.hook,
            "visual": "Black glass dashboard, red risk pulse, one decisive stat.",
        },
        {
            "slide": "2",
            "headline": "The real enemy is invisible drift",
            "visual": "Before/after workflow with missing logs highlighted.",
        },
        {
            "slide": "3",
            "headline": "Build the enforcement layer",
            "visual": "Inputs → model → policy → human gate → audit ledger.",
        },
        {
            "slide": "4",
            "headline": "Measure trust like revenue",
            "visual": "Precision, recall, latency, override rate, pipeline value.",
        },
        {
            "slide": "5",
            "headline": f"Get the {pillar['offer']}",
            "visual": f"CTA card with {url}",
        },
    ]


def video_script(concept: Concept, pillar: dict[str, str]) -> list[dict[str, str]]:
    url = utm_url(pillar, "youtube", concept.id, "shorts")
    return [
        {
            "time": "0-3s",
            "visual": "Fast zoom into terminal + risk dashboard",
            "voiceover": concept.hook,
        },
        {
            "time": "4-12s",
            "visual": "Split-screen: hype demo vs. audit log",
            "voiceover": "The demo looks magical. The audit trail is usually empty.",
        },
        {
            "time": "13-28s",
            "visual": "Draw the five-layer stack",
            "voiceover": "Inputs, outputs, human oversight, decision trails, continuous monitoring.",
        },
        {
            "time": "29-45s",
            "visual": "Python tests and eval scorecard flash by",
            "voiceover": "Every operator correction becomes an eval. Only winning versions get promoted.",
        },
        {
            "time": "46-55s",
            "visual": "Executive dashboard: ROI + risk",
            "voiceover": f"That is how {pillar['keyword']} become board-safe and revenue-ready.",
        },
        {
            "time": "56-60s",
            "visual": "CTA card",
            "voiceover": f"Download the framework at {url}",
        },
    ]


def asset_pack(concept: Concept) -> dict[str, Any]:
    pillar = PILLARS[concept.pillar]
    return {
        "concept": asdict(concept),
        "pillar": pillar,
        "conversion_urls": {
            source: utm_url(pillar, source, concept.id, "social")
            for source in ["linkedin", "x", "youtube", "instagram"]
        },
        "seo_blog_outline": seo_outline(concept, pillar),
        "linkedin_post": linkedin_post(concept, pillar),
        "x_thread": x_thread(concept, pillar),
        "linkedin_carousel": carousel(concept, pillar),
        "video_script_60s": video_script(concept, pillar),
        "hashtags": [
            "#AI",
            "#Cybersecurity",
            "#OSINT",
            "#LegalTech",
            "#Leadership",
            "#AuditableAI",
            "#ClearGlassInc",
        ],
    }


def dashboard(packs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "week_id": WEEK_ID,
        "targets_90_day": {
            "assets_generated": 90,
            "linkedin_engagement_rate": 0.05,
            "x_impressions": 500000,
            "lead_magnet_downloads": 100,
            "ai_answer_box_citations": 3,
            "google_ranking_target": "top_3:auditable AI systems",
            "time_saved_hours_per_week": 15,
            "revenue_target_usd": [250000, 1000000],
        },
        "weekly_pack": {
            "concept_count": len(packs),
            "asset_count": len(packs) * 5,
            "formats": [
                "seo_blog_outline",
                "linkedin_post",
                "x_thread",
                "linkedin_carousel",
                "video_script_60s",
            ],
        },
        "events_to_track": [
            "impression",
            "engagement",
            "profile_click",
            "landing_page_view",
            "form_submit",
            "consult_booked",
            "proposal_sent",
            "closed_won",
        ],
        "utm_dimensions": ["utm_source", "utm_medium", "utm_campaign", "utm_content"],
    }


def generate(out_dir: Path) -> tuple[Path, Path]:
    concepts = [Concept(*row) for row in CONCEPTS]
    packs = [asset_pack(c) for c in concepts]
    out_dir.mkdir(parents=True, exist_ok=True)
    pack_path = out_dir / f"weekly_content_{WEEK_ID}.json"
    dash_path = out_dir / f"analytics_dashboard_{WEEK_ID}.json"
    pack_path.write_text(
        json.dumps({"week_id": WEEK_ID, "assets": packs}, indent=2) + "\n"
    )
    dash_path.write_text(json.dumps(dashboard(packs), indent=2) + "\n")
    return pack_path, dash_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="marketing/output/weekly")
    args = parser.parse_args()
    pack, dash = generate(Path(args.out_dir))
    print(f"Generated {pack}")
    print(f"Generated {dash}")


if __name__ == "__main__":
    main()
