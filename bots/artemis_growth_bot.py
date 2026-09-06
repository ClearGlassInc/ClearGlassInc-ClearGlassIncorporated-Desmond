# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "marketing" / "output"
THREADS_JSON = OUTPUT_DIR / "threads_latest.json"
THREADS_MD = OUTPUT_DIR / "threads_latest.md"
CAMPAIGN_JSON = OUTPUT_DIR / "campaign_latest.json"
CAMPAIGN_MD = OUTPUT_DIR / "campaign_latest.md"
THREADS_ARCHIVE_DIR = OUTPUT_DIR / "threads_archive"
SITE_PAGE = ROOT / "threads.html"

ALLOWED_HOSTS = {"www.clearglassinc.com", "github.com"}
PUBLICATION_MODE = "manual-review-only"
PROHIBITED_PATTERNS = (
    re.compile(r"\bguaranteed\b", re.IGNORECASE),
    re.compile(r"\bviral\b", re.IGNORECASE),
    re.compile(r"\bbuy\s+(?:a\s+)?star", re.IGNORECASE),
    re.compile(r"\bstar\s+for\s+reward", re.IGNORECASE),
    re.compile(r"\bmass[-\s]?message", re.IGNORECASE),
    re.compile(r"\bsigned deal\b", re.IGNORECASE),
    re.compile(r"\bgave me my reputation back\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class CampaignLink:
    destination: str
    source: str
    medium: str
    campaign: str
    content: str

    def render(self) -> str:
        parsed = urlparse(self.destination)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"destination is not allowlisted: {self.destination}")

        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(
            {
                "utm_source": self.source,
                "utm_medium": self.medium,
                "utm_campaign": self.campaign,
                "utm_content": self.content,
            }
        )
        return urlunparse(parsed._replace(query=urlencode(query)))


@dataclass(frozen=True)
class Tweet:
    text: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ThreadBundle:
    thread_number: int
    app_name: str
    audience: str
    objective: str
    tweets: tuple[Tweet, ...]
    cta_url: str


@dataclass(frozen=True)
class CampaignAsset:
    channel: str
    asset: str
    objective: str
    copy: str
    destination: str
    evidence: tuple[str, ...]
    review_required: bool = True


@dataclass(frozen=True)
class GrowthRun:
    run_utc: str
    app_name: str
    total_threads: int
    total_assets: int
    output_dir: str
    site_page: str
    publication_mode: str


def _tracked_link(source: str, medium: str, content: str) -> str:
    return CampaignLink(
        destination="https://www.clearglassinc.com/",
        source=source,
        medium=medium,
        campaign="artemis_launch",
        content=content,
    ).render()


def _validate_copy(text: str) -> None:
    if "[" in text or "]" in text:
        raise ValueError("campaign copy contains unresolved placeholder syntax")
    for pattern in PROHIBITED_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"campaign copy contains prohibited pattern: {pattern.pattern}")


def _validate_evidence(evidence: tuple[str, ...]) -> None:
    if not evidence:
        raise ValueError("every campaign asset must cite repository evidence")
    for ref in evidence:
        if ref.startswith(("http://", "https://")):
            raise ValueError("evidence must be repository paths, not external URLs")
        if ".." in Path(ref).parts:
            raise ValueError("evidence path cannot traverse outside the repository")


def build_threads(app_name: str = "ClearGlassInc Artemis") -> list[ThreadBundle]:
    evidence = ("README.md", "docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md")
    site = _tracked_link("x", "organic_social", "proof_thread")

    threads = [
        ThreadBundle(
            thread_number=1,
            app_name=app_name,
            audience="AI/platform engineers",
            objective="Explain the governance boundary",
            cta_url=site,
            tweets=(
                Tweet("A model can recommend the next move. That does not mean it should be allowed to authorize it.", evidence),
                Tweet("Artemis separates evidence, policy, approval, execution, and audit instead of treating model confidence as authority.", evidence),
                Tweet("The practical question is simple: where does authorization live when an agent can call tools?", evidence),
                Tweet(f"Architecture and implementation map: {site}", evidence),
                Tweet("Technical criticism is welcome. Point to the trust boundary you would change first.", evidence),
            ),
        ),
        ThreadBundle(
            thread_number=2,
            app_name=app_name,
            audience="security architects",
            objective="Show security posture",
            cta_url=_tracked_link("x", "organic_social", "security_thread"),
            tweets=(
                Tweet("Agentic systems fail when policy exists only in prompts.", evidence),
                Tweet("Artemis treats model output as untrusted data and keeps consequential authorization in deterministic controls outside the model.", evidence),
                Tweet("That means typed tools, risk gates, explicit approval paths, provenance, and reversible deployment.", evidence),
                Tweet(f"Review the live product surface and repository evidence: {_tracked_link('x', 'organic_social', 'security_thread')}", evidence),
                Tweet("The standard is not 'does the demo work?' It is 'can the decision path be audited and reversed?'", evidence),
            ),
        ),
        ThreadBundle(
            thread_number=3,
            app_name=app_name,
            audience="technical founders",
            objective="Frame the repository as a product system",
            cta_url=_tracked_link("x", "organic_social", "founder_thread"),
            tweets=(
                Tweet("A repository earns adoption when a visitor can understand the problem, verify the proof, run the system, and know where to contribute.", evidence),
                Tweet("That is why Artemis is being operated as a conversion funnel: discovery → README trust → live product → activation → contribution.", ("docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md",)),
                Tweet("No fake stars. No bulk promotion. No invented customer proof. The growth engine is documentation, demos, releases, and useful technical artifacts.", ("docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md",)),
                Tweet(f"Explore the current system: {_tracked_link('x', 'organic_social', 'founder_thread')}", evidence),
                Tweet("If the quick start or architecture map creates friction, open a focused issue with the exact failing step.", evidence),
            ),
        ),
        ThreadBundle(
            thread_number=4,
            app_name=app_name,
            audience="automation builders",
            objective="Invite reproducible use cases",
            cta_url=_tracked_link("x", "organic_social", "automation_thread"),
            tweets=(
                Tweet("The useful agent loop is not 'prompt → magic.'", evidence),
                Tweet("It is evidence → bounded plan → policy check → approval where required → execution → audit.", evidence),
                Tweet("That structure makes failures observable and recovery possible.", evidence),
                Tweet(f"See how the pieces fit together: {_tracked_link('x', 'organic_social', 'automation_thread')}", evidence),
                Tweet("If you adapt the pattern to another domain, document the trust boundary and failure mode. That is the contribution worth sharing.", evidence),
            ),
        ),
        ThreadBundle(
            thread_number=5,
            app_name=app_name,
            audience="open-source contributors",
            objective="Convert attention into contribution",
            cta_url=_tracked_link("x", "organic_social", "contributor_thread"),
            tweets=(
                Tweet("Launch week is not the finish line. It is an evaluation window.", ("docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md",)),
                Tweet("The useful signals are setup failures, architecture critiques, missing docs, reproducible bugs, and real integrations.", ("docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md",)),
                Tweet("Stars are interest. They are not proof of adoption.", ("docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md",)),
                Tweet(f"Start with the repository map and live platform: {_tracked_link('x', 'organic_social', 'contributor_thread')}", evidence),
                Tweet("Contribute one focused improvement with verification evidence. That compounds better than engagement tricks.", evidence),
            ),
        ),
    ]

    for thread in threads:
        for tweet in thread.tweets:
            _validate_copy(tweet.text)
            _validate_evidence(tweet.evidence)
    return threads


def build_campaign_assets(app_name: str = "ClearGlassInc Artemis") -> list[CampaignAsset]:
    base_evidence = ("README.md", "docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md")
    assets = [
        CampaignAsset(
            channel="linkedin",
            asset="launch_post",
            objective="Drive qualified repository and website visits",
            destination=_tracked_link("linkedin", "organic_social", "launch_post"),
            evidence=base_evidence,
            copy=(
                f"{app_name} is built for teams that need AI systems to remain auditable when decisions become consequential.\n\n"
                "The system separates model output from authority through evidence lineage, deterministic policy, explicit approvals, and reversible execution.\n\n"
                "The repository includes the architecture map, implementation surfaces, security model, tests, and contribution path.\n\n"
                f"Explore the live platform: {_tracked_link('linkedin', 'organic_social', 'launch_post')}\n\n"
                "Technical question: which trust boundary would you inspect first?"
            ),
        ),
        CampaignAsset(
            channel="x",
            asset="launch_post",
            objective="Create technical curiosity without unsupported claims",
            destination=_tracked_link("x", "organic_social", "launch_post"),
            evidence=base_evidence,
            copy=(
                "A model can recommend the next move. It should not manufacture the authority to execute it.\n\n"
                "ClearGlassInc Artemis separates evidence → policy → approval → execution → audit.\n\n"
                f"Architecture + live platform: {_tracked_link('x', 'organic_social', 'launch_post')}\n\n"
                "What trust boundary would you challenge first?"
            ),
        ),
        CampaignAsset(
            channel="reddit",
            asset="technical_feedback",
            objective="Request architecture feedback in relevant communities",
            destination=_tracked_link("reddit", "community", "technical_feedback"),
            evidence=base_evidence,
            copy=(
                f"{app_name} — governed agentic infrastructure for high-assurance workflows.\n\n"
                "I built this around a specific design constraint: model output is untrusted until deterministic policy and, where required, human approval make the transition valid.\n\n"
                "I would especially value technical feedback on setup friction, trust boundaries, missing integrations, and production-readiness concerns.\n\n"
                f"Repository and live platform: {_tracked_link('reddit', 'community', 'technical_feedback')}\n\n"
                "This is a focused request for technical criticism, not bulk promotion."
            ),
        ),
        CampaignAsset(
            channel="devto",
            asset="article_brief",
            objective="Convert repository architecture into an educational article",
            destination=_tracked_link("devto", "earned_content", "architecture_article"),
            evidence=base_evidence + ("docs/clearglassinc_artemis_self_evolving_platform.md",),
            copy=(
                "Title: Building an AI Control Plane That Cannot Manufacture Its Own Authority\n\n"
                "Cover the problem, trust boundaries, typed tools, deterministic policy, approval states, audit evidence, rollback, and what remains target-state rather than deployed.\n\n"
                f"Canonical project destination: {_tracked_link('devto', 'earned_content', 'architecture_article')}"
            ),
        ),
        CampaignAsset(
            channel="hackernews",
            asset="show_hn",
            objective="Invite architecture and operational-model critique",
            destination=_tracked_link("hackernews", "community", "show_hn"),
            evidence=base_evidence,
            copy=(
                "Show HN: ClearGlassInc Artemis — governed agent infrastructure with explicit authorization boundaries\n\n"
                "I built Artemis to separate model recommendations from operational authority. The repository combines policy-constrained agents, evidence lineage, approval gates, audit trails, and deployable product surfaces.\n\n"
                "The part I would value criticism on most is the boundary between autonomous analysis and consequential execution.\n\n"
                f"Project: {_tracked_link('hackernews', 'community', 'show_hn')}"
            ),
        ),
    ]

    for asset in assets:
        _validate_copy(asset.copy)
        _validate_evidence(asset.evidence)
        parsed = urlparse(asset.destination)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"invalid campaign destination: {asset.destination}")
        if not asset.review_required:
            raise ValueError("growth assets must remain human-review gated")
    return assets


def render_threads_markdown(threads: list[ThreadBundle]) -> str:
    lines: list[str] = [
        "# ClearGlassInc Artemis Proof-Led Threads Pack",
        "",
        "> DRAFT — HUMAN REVIEW REQUIRED. No asset in this file is approved for automatic publication.",
        "",
    ]
    for thread in threads:
        lines.extend(
            [
                f"## Thread {thread.thread_number}: {thread.objective}",
                "",
                f"- Audience: {thread.audience}",
                f"- CTA: {thread.cta_url}",
                "",
            ]
        )
        for idx, tweet in enumerate(thread.tweets, start=1):
            lines.append(f"{idx}. {tweet.text}")
            lines.append(f"   - Evidence: {', '.join(tweet.evidence)}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_campaign_markdown(assets: list[CampaignAsset]) -> str:
    lines = [
        "# ClearGlassInc Artemis Campaign Pack",
        "",
        "> DRAFT — HUMAN REVIEW REQUIRED. Publication mode: manual review only.",
        "",
    ]
    for asset in assets:
        lines.extend(
            [
                f"## {asset.channel}: {asset.asset}",
                "",
                f"**Objective:** {asset.objective}",
                f"**Destination:** {asset.destination}",
                f"**Evidence:** {', '.join(asset.evidence)}",
                "",
                asset.copy,
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def render_site_page(threads: list[ThreadBundle], assets: list[CampaignAsset]) -> str:
    thread_cards = []
    for thread in threads:
        tweets = "\n".join(
            f'<li><span class="tweet-index">{i}.</span> {tweet.text}</li>'
            for i, tweet in enumerate(thread.tweets, start=1)
        )
        thread_cards.append(
            f"""
      <article class="card">
        <p class="eyebrow">Thread {thread.thread_number} · {thread.audience}</p>
        <h2>{thread.objective}</h2>
        <ul>{tweets}</ul>
        <p><a href="{thread.cta_url}">Tracked campaign destination →</a></p>
      </article>
"""
        )

    asset_cards = []
    for asset in assets:
        asset_cards.append(
            f"""
      <article class="card">
        <p class="eyebrow">{asset.channel} · {asset.asset}</p>
        <h2>{asset.objective}</h2>
        <pre>{asset.copy}</pre>
        <p class="evidence">Evidence: {', '.join(asset.evidence)}</p>
      </article>
"""
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="noindex,nofollow" />
  <title>ClearGlassInc Artemis Campaign Review Kit</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; margin: 0; background: #070b12; color: #e5e7eb; }}
    nav {{ position: sticky; top: 0; z-index: 20; display: flex; justify-content: space-between; padding: 18px clamp(1rem,4vw,3rem); background: rgba(7,11,18,.92); border-bottom: 1px solid #243043; }}
    nav a {{ color: #e5e7eb; text-decoration: none; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 48px 20px 72px; }}
    h1 {{ font-size: clamp(2rem, 5vw, 3.4rem); margin: 0 0 12px; }}
    .notice {{ border: 1px solid #6b7280; border-radius: 12px; padding: 14px 16px; background: #111827; }}
    .grid {{ display: grid; gap: 16px; margin-top: 24px; }}
    .card {{ border: 1px solid #243043; border-radius: 16px; padding: 20px; background: #0f172a; }}
    .eyebrow {{ color: #7dd3fc; font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; }}
    ul {{ padding-left: 20px; }}
    li {{ margin: 10px 0; line-height: 1.55; }}
    pre {{ white-space: pre-wrap; font: inherit; line-height: 1.6; background: #020617; padding: 16px; border-radius: 10px; overflow-x: auto; }}
    a {{ color: #7dd3fc; }}
    .evidence {{ color: #94a3b8; font-size: .9rem; }}
  </style>
</head>
<body>
  <nav><a href="index.html">ClearGlass Inc.</a><span>Campaign review surface</span></nav>
  <main>
    <h1>Artemis Growth Engine</h1>
    <p class="notice"><strong>DRAFT — HUMAN REVIEW REQUIRED.</strong> This page is a review surface. It does not publish, message users, buy engagement, or claim unverified results.</p>

    <h2>Proof-led technical threads</h2>
    <div class="grid">{''.join(thread_cards)}</div>

    <h2>Channel assets</h2>
    <div class="grid">{''.join(asset_cards)}</div>
  </main>
</body>
</html>
"""


def write_outputs(app_name: str = "ClearGlassInc Artemis") -> GrowthRun:
    threads = build_threads(app_name)
    assets = build_campaign_assets(app_name)
    run = GrowthRun(
        run_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        app_name=app_name,
        total_threads=len(threads),
        total_assets=len(assets),
        output_dir=str(OUTPUT_DIR.relative_to(ROOT)),
        site_page=str(SITE_PAGE.relative_to(ROOT)),
        publication_mode=PUBLICATION_MODE,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    THREADS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    threads_payload = {
        "run": asdict(run),
        "threads": [
            {
                "thread_number": thread.thread_number,
                "app_name": thread.app_name,
                "audience": thread.audience,
                "objective": thread.objective,
                "cta_url": thread.cta_url,
                "tweets": [asdict(tweet) for tweet in thread.tweets],
            }
            for thread in threads
        ],
    }
    campaign_payload = {
        "run": asdict(run),
        "assets": [asdict(asset) for asset in assets],
    }

    THREADS_JSON.write_text(json.dumps(threads_payload, indent=2) + "\n", encoding="utf-8")
    THREADS_MD.write_text(render_threads_markdown(threads), encoding="utf-8")
    CAMPAIGN_JSON.write_text(json.dumps(campaign_payload, indent=2) + "\n", encoding="utf-8")
    CAMPAIGN_MD.write_text(render_campaign_markdown(assets), encoding="utf-8")

    stamp = run.run_utc.replace("+00:00", "Z").replace(":", "")
    (THREADS_ARCHIVE_DIR / f"{stamp}.md").write_text(
        render_threads_markdown(threads),
        encoding="utf-8",
    )
    SITE_PAGE.write_text(render_site_page(threads, assets), encoding="utf-8")

    return run


if __name__ == "__main__":
    result = write_outputs()
    print(f"Artemis Growth Engine complete for {result.app_name}")
    print(f"Generated {result.total_threads} threads and {result.total_assets} campaign assets")
    print(f"Publication mode: {result.publication_mode}")
    print(f"Updated review surface: {result.site_page}")
