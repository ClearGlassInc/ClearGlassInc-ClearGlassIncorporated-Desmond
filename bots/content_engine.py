# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""
ClearGlassInc Content Engine

Daily content pipeline: selects a brand pillar, generates platform-specific
copy for LinkedIn, Threads, X, email, and website updates, then writes
structured output for downstream validation, scheduling, and publishing.

Pillar rotation: daily (day-of-year % 4).
Variant rotation: weekly (ISO week % num_variants) — prevents repetition.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "marketing" / "output"
PLATFORMS_DIR = OUTPUT_DIR / "platforms"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
METRICS_DIR = OUTPUT_DIR / "metrics"

SITE_URL = "https://www.clearglassinc.com/"
URLS = {
    "home": SITE_URL,
    "artemis": f"{SITE_URL}artemis.html",
    "guardian": f"{SITE_URL}guardian.html",
    "threads_kit": f"{SITE_URL}threads.html",
}

PILLARS = ["brand", "artemis", "guardian", "founder"]

PLATFORM_LIMITS: dict[str, dict[str, int]] = {
    "linkedin": {"min": 300, "max": 3000},
    "threads": {"min": 50, "max": 500},
    "x": {"min": 30, "max": 280},
    "email": {"min": 200, "max": 5000},
    "website": {"min": 80, "max": 400},
}

# ── Content variants: pillar → platform → list[variant dict] ──────────────────
# Variants rotate weekly so daily runs within the same week share a voice,
# but consecutive weeks produce meaningfully different copy.

CONTENT: dict[str, dict[str, list[dict[str, Any]]]] = {
    "brand": {
        "linkedin": [
            {
                "headline": "Clarity is not a feature. It is a force multiplier.",
                "body": (
                    "In cybersecurity the organizations that survive are not the ones with the "
                    "most tools. They are the ones with the clearest picture.\n\n"
                    "ClearGlass Inc was built around one principle: transparent intelligence "
                    "creates irreversible advantage. Our platform surfaces what matters, strips "
                    "what does not, and delivers a clean operational signal to the people "
                    "responsible for acting on it.\n\n"
                    "This is not a positioning statement. It is the architectural philosophy "
                    "behind every product we ship.\n\n"
                    "When your security posture is legible to the executives who own it, you "
                    "respond faster, report cleaner, and hold ground under pressure.\n\n"
                    "Clarity is power. We build the lens.\n\n"
                    "→ {home}"
                ),
                "cta_url": "home",
                "labels": ["pillar:brand", "platform:linkedin", "urgency:normal"],
            },
            {
                "headline": "The premium brand in security does not shout. It demonstrates.",
                "body": (
                    "Every enterprise security vendor claims sophistication. Most deliver "
                    "complexity dressed as intelligence.\n\n"
                    "ClearGlass Inc operates differently. We do not compete on feature count. "
                    "We compete on operational clarity.\n\n"
                    "Our products — Artemis and Guardian — are designed for the decision-maker "
                    "who needs signal, not noise; outcomes, not activity metrics.\n\n"
                    "We built this company for CISOs, CTOs, and founders who understand that "
                    "security is not a cost center. It is the infrastructure of trust.\n\n"
                    "If your team spends more time managing the security stack than acting on "
                    "its intelligence, something is wrong with the stack. We fix that.\n\n"
                    "→ {home}"
                ),
                "cta_url": "home",
                "labels": ["pillar:brand", "platform:linkedin", "urgency:normal"],
            },
        ],
        "threads": [
            {
                "posts": [
                    "Clarity is not a feature. It's a strategic posture.",
                    "Most security tools add complexity and call it capability. ClearGlass removes complexity to reveal what's real.",
                    "The organizations that survive breaches aren't the ones with the most alerts — they're the ones who acted on the right signal.",
                    "That's what we build at ClearGlass: the lens, not the noise.",
                    "→ www.clearglassinc.com",
                ],
            },
            {
                "posts": [
                    "Premium brands in security don't sell software. They sell trust.",
                    "ClearGlass was built for operators who need to act — not analyze dashboards for 40 minutes.",
                    "Every product we ship passes one test: does it make the right decision obvious?",
                    "If it doesn't, it doesn't ship.",
                    "→ www.clearglassinc.com",
                ],
            },
        ],
        "x": [
            {"text": "Clarity is not a feature. It's a force multiplier. ClearGlass Inc builds the lens. {home}"},
            {"text": "Most security tools add complexity. ClearGlass strips it. Signal over noise — every time. {home}"},
        ],
        "email": [
            {
                "subject": "Why clarity is ClearGlass Inc's primary product",
                "preview": "The organizations that survive aren't the ones with the most tools.",
                "body": (
                    "In cybersecurity the difference between survival and compromise often comes "
                    "down to one factor: how fast you can see what's real.\n\n"
                    "ClearGlass Inc was founded on the belief that transparent intelligence is the "
                    "ultimate competitive advantage. Not more dashboards. Not more alerts. Clarity.\n\n"
                    "Our products — Artemis and Guardian — are built from a single principle: "
                    "surface what matters, strip what doesn't, deliver a clean signal to the people "
                    "responsible for acting on it.\n\n"
                    "If you're evaluating your security posture this quarter, start here: {home}\n\n"
                    "— The ClearGlass Team"
                ),
                "cta_url": "home",
                "labels": ["pillar:brand", "platform:email", "urgency:normal"],
            },
        ],
        "website": [
            {"section": "brand-statement", "copy": "Clarity is power. ClearGlass Inc builds the intelligence layer for organizations operating at the edge of acceptable risk."},
            {"section": "brand-statement", "copy": "Transparent intelligence. Disciplined execution. Long-horizon infrastructure built for organizations that cannot afford to be wrong."},
        ],
    },

    "artemis": {
        "linkedin": [
            {
                "headline": "Artemis turns your security stack into a coherent intelligence surface.",
                "body": (
                    "Most enterprise security deployments share the same structural flaw: they "
                    "produce volume, not intelligence.\n\n"
                    "Dozens of tools. Thousands of alerts. Zero coherent signal.\n\n"
                    "Artemis — ClearGlass Inc's flagship platform — was engineered to solve this "
                    "at the architectural level. Not by adding another integration layer. By "
                    "replacing the signal architecture entirely.\n\n"
                    "Artemis connects your existing telemetry sources, normalizes the signal, "
                    "applies continuous threat modeling, and surfaces a prioritized operational "
                    "picture for your security leadership.\n\n"
                    "The result: your team acts on what matters — instead of triaging what doesn't.\n\n"
                    "→ {artemis}"
                ),
                "cta_url": "artemis",
                "labels": ["pillar:artemis", "platform:linkedin", "urgency:normal"],
            },
            {
                "headline": "The architecture behind Artemis: why digital-twin operations change the game.",
                "body": (
                    "Artemis is not a SIEM replacement. It is a different category of system.\n\n"
                    "At its core, Artemis builds a living digital twin of your operational "
                    "environment — one that reflects actual system state, active threat vectors, "
                    "and exposure drift in real time.\n\n"
                    "Your security picture is never a snapshot. It is a continuous, self-updating "
                    "map of your exposure.\n\n"
                    "Three things this changes immediately:\n"
                    "1. Detection latency drops from days to hours.\n"
                    "2. Incident response becomes coordinatable, not reactive.\n"
                    "3. Executive reporting reflects operational reality, not lagging indicators.\n\n"
                    "This is enterprise-grade intelligence infrastructure. Built for organizations "
                    "that cannot afford to be wrong.\n\n"
                    "→ {artemis}"
                ),
                "cta_url": "artemis",
                "labels": ["pillar:artemis", "platform:linkedin", "urgency:normal"],
            },
        ],
        "threads": [
            {
                "posts": [
                    "Most SIEM deployments are expensive noise generators. Here's what Artemis does differently:",
                    "Artemis doesn't add another integration layer. It replaces the signal architecture.",
                    "Connect telemetry → normalize → model threats continuously → surface a prioritized operational picture.",
                    "Your analysts act on signal. Not on alert volume.",
                    "→ www.clearglassinc.com/artemis.html",
                ],
            },
            {
                "posts": [
                    "What's a digital-twin security operation? Short version:",
                    "Instead of querying your environment reactively, Artemis builds a living model of it.",
                    "System state, active vectors, exposure drift — updated continuously, not at report time.",
                    "Detection latency: hours, not days. Reporting: operational reality, not lagging metrics.",
                    "→ www.clearglassinc.com/artemis.html",
                ],
            },
        ],
        "x": [
            {"text": "Artemis doesn't add another dashboard. It replaces the signal architecture. Your analysts act on intelligence — not volume. {artemis}"},
            {"text": "Digital-twin security ops: your environment, modeled continuously. Exposure drift surfaced before it becomes a breach. That's Artemis. {artemis}"},
        ],
        "email": [
            {
                "subject": "Artemis: when your security stack becomes an intelligence surface",
                "preview": "Stop triaging alerts. Start acting on signal.",
                "body": (
                    "The average enterprise SOC team spends 40% of its time managing the security "
                    "stack — not acting on the intelligence it produces.\n\n"
                    "This is the structural flaw that Artemis was designed to address.\n\n"
                    "Artemis doesn't layer on top of your existing stack. It replaces the signal "
                    "architecture. Connect your telemetry sources, normalize the data, apply "
                    "continuous threat modeling, and surface a prioritized operational picture "
                    "for your security leadership.\n\n"
                    "The practical outcome: your team shifts from reactive triage to proactive "
                    "posture management.\n\n"
                    "→ Review the Artemis platform: {artemis}\n\n"
                    "— The ClearGlass Team"
                ),
                "cta_url": "artemis",
                "labels": ["pillar:artemis", "platform:email", "urgency:normal"],
            },
        ],
        "website": [
            {"section": "artemis-headline", "copy": "Artemis transforms your security telemetry into a coherent intelligence surface — continuous threat modeling, real-time exposure mapping, executive-grade reporting."},
            {"section": "artemis-headline", "copy": "A living digital twin of your operational environment. Artemis surfaces exposure drift, active vectors, and prioritized response actions — continuously, not at report time."},
        ],
    },

    "guardian": {
        "linkedin": [
            {
                "headline": "Guardian: executive-grade hardening for organizations that cannot afford operational risk.",
                "body": (
                    "Security hardening is not the same as compliance.\n\n"
                    "Organizations that conflate the two discover the difference during an incident.\n\n"
                    "Guardian — ClearGlass Inc's operational security platform — was built for the "
                    "gap between compliance checkboxes and operational resilience. It applies "
                    "AI-assisted defense across your attack surface, prioritizes hardening actions "
                    "by risk-adjusted impact, and integrates a clean deployment path that does not "
                    "require a six-month implementation engagement.\n\n"
                    "What you get:\n"
                    "→ Zero-trust posture enforcement at the infrastructure layer\n"
                    "→ AI-driven threat surface reduction — continuous, not periodic\n"
                    "→ Deployment in hours, not quarters\n"
                    "→ Audit-ready output at every stage\n\n"
                    "→ {guardian}"
                ),
                "cta_url": "guardian",
                "labels": ["pillar:guardian", "platform:linkedin", "urgency:normal"],
            },
            {
                "headline": "The difference between a secure organization and a compliant one.",
                "body": (
                    "Compliance is a point-in-time snapshot. Security is a continuous operational posture.\n\n"
                    "Most enterprise security teams know this distinction. Most enterprise tools still "
                    "reward compliance paperwork over operational resilience.\n\n"
                    "Guardian was designed to close that gap. It hardens your environment against "
                    "the actual threat surface — not the hypothetical one that passed last quarter's "
                    "audit — and it does so continuously, with AI-assisted prioritization that tells "
                    "your team exactly where the highest-impact hardening actions are.\n\n"
                    "The result is not a compliance certificate. It is a measurably stronger posture "
                    "with documentation that satisfies both operational review and audit requirements.\n\n"
                    "This is the security investment that pays for itself before the next incident.\n\n"
                    "→ {guardian}"
                ),
                "cta_url": "guardian",
                "labels": ["pillar:guardian", "platform:linkedin", "urgency:normal"],
            },
        ],
        "threads": [
            {
                "posts": [
                    "Compliance is a snapshot. Security is a posture. Here's the difference that matters:",
                    "Most tools optimize for audit paperwork. Guardian optimizes for your actual threat surface.",
                    "AI-assisted hardening prioritized by risk-adjusted impact — continuously, not quarterly.",
                    "You get a stronger posture and the documentation to prove it.",
                    "→ www.clearglassinc.com/guardian.html",
                ],
            },
            {
                "posts": [
                    "Most organizations discover their hardening gaps during incidents. Guardian changes that:",
                    "Zero-trust posture enforcement. AI-driven threat surface reduction. Deployment in hours.",
                    "The gap between 'we passed the audit' and 'we're actually secure' is where breaches live.",
                    "Guardian operates in that gap.",
                    "→ www.clearglassinc.com/guardian.html",
                ],
            },
        ],
        "x": [
            {"text": "Compliance is a snapshot. Security is a posture. Guardian closes the gap — AI-assisted hardening, continuous, not periodic. {guardian}"},
            {"text": "The gap between 'we passed the audit' and 'we're actually secure' is where breaches happen. Guardian operates in that gap. {guardian}"},
        ],
        "email": [
            {
                "subject": "Guardian: the difference between compliant and secure",
                "preview": "Most organizations discover their hardening gaps during incidents.",
                "body": (
                    "There is a critical distinction between compliance and security that most "
                    "enterprise teams understand but most enterprise tools ignore.\n\n"
                    "Compliance is a point-in-time snapshot. Security is a continuous operational posture.\n\n"
                    "Guardian was built to enforce the latter. It applies AI-assisted hardening "
                    "across your attack surface — continuously, prioritized by risk-adjusted impact. "
                    "Not by what looks best in the next audit, but by what actually reduces your "
                    "exposure to active threats.\n\n"
                    "Deployment runs in hours. Audit-ready output is produced at every stage. "
                    "Zero-trust posture enforcement operates at the infrastructure layer.\n\n"
                    "→ Download Guardian: {guardian}\n\n"
                    "— The ClearGlass Team"
                ),
                "cta_url": "guardian",
                "labels": ["pillar:guardian", "platform:email", "urgency:normal"],
            },
        ],
        "website": [
            {"section": "guardian-headline", "copy": "Guardian applies AI-assisted hardening across your attack surface — continuously, prioritized by risk-adjusted impact, deployable in hours."},
            {"section": "guardian-headline", "copy": "Close the gap between compliant and secure. Guardian enforces zero-trust posture at the infrastructure layer and produces audit-ready output at every stage."},
        ],
    },

    "founder": {
        "linkedin": [
            {
                "headline": "What I've learned building security infrastructure for organizations at the edge of acceptable risk.",
                "body": (
                    "Three years building ClearGlass Inc has taught me more about enterprise "
                    "security decision-making than any certification program.\n\n"
                    "The CISO who needs to defend a budget to a board that doesn't understand "
                    "threat modeling. The security team that's been alert-fatigued so long that "
                    "high-severity events get triaged like noise. The founder who knows their "
                    "product is secure but can't articulate it to investors.\n\n"
                    "These are real operational problems. Not technical ones.\n\n"
                    "The technology is usually available. What's missing is the intelligence "
                    "architecture — the system that translates raw security telemetry into "
                    "decisions that executives can act on.\n\n"
                    "That's what we build at ClearGlass. Not security tools. Security intelligence.\n\n"
                    "The distinction matters because tools require operators. Intelligence enables "
                    "decisions.\n\n"
                    "→ {home}"
                ),
                "cta_url": "home",
                "labels": ["pillar:founder", "platform:linkedin", "urgency:normal"],
            },
            {
                "headline": "The hardest part of building a security company is not the technology.",
                "body": (
                    "The hardest part is convincing organizations that the risk is real before "
                    "the incident that makes it obvious.\n\n"
                    "At ClearGlass Inc we work with organizations that operate at the edge of "
                    "acceptable risk — government, financial institutions, enterprise technology.\n\n"
                    "These are sophisticated buyers. They've seen every security vendor pitch. "
                    "They know the difference between capability and marketing language.\n\n"
                    "What earns their trust is not our feature list. It is operational clarity.\n\n"
                    "When we show a CISO a clean intelligence surface — one that reflects their "
                    "actual environment, not a template dashboard — the conversation changes. "
                    "They stop evaluating vendors. They start planning deployments.\n\n"
                    "That is the only kind of credibility that matters in this market.\n\n"
                    "→ {home}"
                ),
                "cta_url": "home",
                "labels": ["pillar:founder", "platform:linkedin", "urgency:normal"],
            },
        ],
        "threads": [
            {
                "posts": [
                    "Three years building security infrastructure. Here's what actually earns enterprise trust:",
                    "Not the feature list. Not the compliance certifications.",
                    "Operational clarity — showing a CISO their actual environment, not a template dashboard.",
                    "When the picture is clean and accurate, they stop evaluating and start deploying.",
                    "→ www.clearglassinc.com",
                ],
            },
            {
                "posts": [
                    "The hardest part of building a security company isn't the technology.",
                    "It's convincing organizations the risk is real before the incident that makes it obvious.",
                    "We work with orgs at the edge of acceptable risk — gov, finance, enterprise tech.",
                    "What earns their trust? Clarity. Every time.",
                    "→ www.clearglassinc.com",
                ],
            },
        ],
        "x": [
            {"text": "The hardest part of building a security company: convincing orgs the risk is real before the incident that makes it obvious. www.clearglassinc.com"},
            {"text": "Show a CISO their actual environment — not a template dashboard — and they stop evaluating vendors and start deploying. That's the only credibility that matters. {home}"},
        ],
        "email": [
            {
                "subject": "From the founder: what I've learned building security intelligence infrastructure",
                "preview": "The hardest part is not the technology.",
                "body": (
                    "Three years building ClearGlass Inc has given me a clear view of where "
                    "enterprise security decision-making breaks down.\n\n"
                    "It's rarely the technical layer. The threats are real and well-understood. "
                    "Detection capabilities exist. Response playbooks are written.\n\n"
                    "What's missing, consistently, is the intelligence architecture — the system "
                    "that translates security telemetry into decisions that executives can actually "
                    "act on.\n\n"
                    "A CISO operating under audit pressure doesn't need another alert. They need "
                    "a clean signal that tells them what to do and how to document the decision.\n\n"
                    "That's the product I set out to build. And it's what drives every "
                    "architectural decision we make at ClearGlass.\n\n"
                    "→ {home}\n\n"
                    "Desmond Otieno Odhiambo\n"
                    "Founder, ClearGlass Inc"
                ),
                "cta_url": "home",
                "labels": ["pillar:founder", "platform:email", "urgency:high"],
            },
        ],
        "website": [
            {"section": "founder-note", "copy": "ClearGlass Inc was built to give security teams the intelligence architecture they need to make decisions under pressure — not just more alerts."},
            {"section": "founder-note", "copy": "ClearGlass Inc — founded by Desmond Otieno Odhiambo. Built for organizations that operate at the edge of acceptable risk and cannot afford to be wrong."},
        ],
    },
}


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlatformContent:
    platform: str
    char_count: int
    content: dict[str, Any]


@dataclass(frozen=True)
class ContentBundle:
    run_utc: str
    pillar: str
    variant_index: int
    day_of_year: int
    iso_week: int
    content_hash: str
    platforms: list[PlatformContent]
    cta_urls: dict[str, str]


# ── Selection logic ───────────────────────────────────────────────────────────

def choose_pillar(now: datetime) -> str:
    forced = os.getenv("FORCE_PILLAR", "").strip().lower()
    if forced in PILLARS:
        return forced
    return PILLARS[now.timetuple().tm_yday % len(PILLARS)]


def choose_variant(variants: list, now: datetime) -> tuple[Any, int]:
    idx = now.isocalendar()[1] % len(variants)
    return variants[idx], idx


# ── URL substitution ──────────────────────────────────────────────────────────

def _resolve_urls(text: str) -> str:
    for key, url in URLS.items():
        text = text.replace("{" + key + "}", url)
    return text


def _resolve_content(obj: Any) -> Any:
    if isinstance(obj, str):
        return _resolve_urls(obj)
    if isinstance(obj, list):
        return [_resolve_content(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _resolve_content(v) for k, v in obj.items()}
    return obj


# ── Bundle construction ───────────────────────────────────────────────────────

def build_bundle(now: datetime | None = None) -> ContentBundle:
    if now is None:
        now = datetime.now(timezone.utc)

    pillar = choose_pillar(now)
    pillar_content = CONTENT[pillar]

    platforms: list[PlatformContent] = []
    variant_idx = -1

    for platform, variants in pillar_content.items():
        variant, variant_idx = choose_variant(variants, now)
        resolved = _resolve_content(variant)

        if platform == "threads":
            raw_text = " ".join(resolved.get("posts", []))
        elif platform == "x":
            raw_text = resolved.get("text", "")
        elif platform == "website":
            raw_text = resolved.get("copy", "")
        elif platform == "email":
            raw_text = resolved.get("subject", "") + " " + resolved.get("body", "")
        else:  # linkedin
            raw_text = resolved.get("headline", "") + " " + resolved.get("body", "")

        platforms.append(PlatformContent(
            platform=platform,
            char_count=len(raw_text),
            content=resolved,
        ))

    bundle_str = json.dumps(
        {"pillar": pillar, "variant": variant_idx, "day": now.timetuple().tm_yday},
        sort_keys=True,
    )
    content_hash = hashlib.sha256(bundle_str.encode()).hexdigest()[:12]

    return ContentBundle(
        run_utc=now.replace(microsecond=0).isoformat(),
        pillar=pillar,
        variant_index=variant_idx,
        day_of_year=now.timetuple().tm_yday,
        iso_week=now.isocalendar()[1],
        content_hash=content_hash,
        platforms=platforms,
        cta_urls=URLS,
    )


# ── Markdown rendering ────────────────────────────────────────────────────────

def _render_linkedin(c: dict) -> str:
    return f"# {c.get('headline', '')}\n\n{c.get('body', '')}\n"


def _render_threads(c: dict) -> str:
    posts = c.get("posts", [])
    lines = [f"{i + 1}. {post}" for i, post in enumerate(posts)]
    return "\n".join(lines) + "\n"


def _render_x(c: dict) -> str:
    return c.get("text", "") + "\n"


def _render_email(c: dict) -> str:
    return (
        f"Subject: {c.get('subject', '')}\n"
        f"Preview: {c.get('preview', '')}\n\n"
        f"{c.get('body', '')}\n"
    )


def _render_website(c: dict) -> str:
    return f"[{c.get('section', 'update')}]\n{c.get('copy', '')}\n"


RENDERERS = {
    "linkedin": _render_linkedin,
    "threads": _render_threads,
    "x": _render_x,
    "email": _render_email,
    "website": _render_website,
}


def render_summary_markdown(bundle: ContentBundle) -> str:
    lines = [
        "# ClearGlass Content Engine Output",
        "",
        f"- Run (UTC): {bundle.run_utc}",
        f"- Pillar: {bundle.pillar}",
        f"- Variant index: {bundle.variant_index}",
        f"- ISO week: {bundle.iso_week}",
        f"- Content hash: {bundle.content_hash}",
        "",
    ]
    for pc in bundle.platforms:
        lines += [
            f"## {pc.platform.title()} ({pc.char_count} chars)",
            "",
            RENDERERS[pc.platform](pc.content),
            "",
        ]
    return "\n".join(lines)


# ── Output writers ────────────────────────────────────────────────────────────

def write_outputs(bundle: ContentBundle) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    for pc in bundle.platforms:
        platform_dir = PLATFORMS_DIR / pc.platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        md = RENDERERS[pc.platform](pc.content)
        (platform_dir / "latest.md").write_text(md, encoding="utf-8")

    summary_md = render_summary_markdown(bundle)
    (OUTPUT_DIR / "latest.md").write_text(summary_md, encoding="utf-8")

    bundle_dict = asdict(bundle)
    (OUTPUT_DIR / "latest.json").write_text(
        json.dumps(bundle_dict, indent=2) + "\n", encoding="utf-8"
    )

    stamp = bundle.run_utc.replace("+00:00", "Z").replace(":", "")
    (ARCHIVE_DIR / f"{stamp}.md").write_text(summary_md, encoding="utf-8")
    (ARCHIVE_DIR / f"{stamp}.json").write_text(
        json.dumps(bundle_dict, indent=2) + "\n", encoding="utf-8"
    )

    metrics_file = METRICS_DIR / "runs.json"
    runs: list[dict] = []
    if metrics_file.exists():
        try:
            runs = json.loads(metrics_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            runs = []

    runs.append({
        "run_utc": bundle.run_utc,
        "pillar": bundle.pillar,
        "variant_index": bundle.variant_index,
        "iso_week": bundle.iso_week,
        "content_hash": bundle.content_hash,
        "platforms": [p.platform for p in bundle.platforms],
    })

    metrics_file.write_text(json.dumps(runs[-500:], indent=2) + "\n", encoding="utf-8")


def emit_github_output(bundle: ContentBundle) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return
    with open(output_file, "a", encoding="utf-8") as fh:
        fh.write(f"pillar={bundle.pillar}\n")
        fh.write(f"content_hash={bundle.content_hash}\n")
        fh.write(f"iso_week={bundle.iso_week}\n")
        fh.write(f"variant_index={bundle.variant_index}\n")


if __name__ == "__main__":
    bundle = build_bundle()
    write_outputs(bundle)
    emit_github_output(bundle)
    print(f"Content engine: pillar={bundle.pillar} hash={bundle.content_hash} week={bundle.iso_week}")
    print(f"Platforms: {', '.join(p.platform for p in bundle.platforms)}")
    print(f"Output: {OUTPUT_DIR}")
