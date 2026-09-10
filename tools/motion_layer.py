#!/usr/bin/env python3
"""Attach the ClearGlass Cinematic Motion System to the static site.

    python3 tools/motion_layer.py            # apply (idempotent)
    python3 tools/motion_layer.py --check    # exit 1 if any page is stale
    python3 tools/motion_layer.py --dry-run  # report without writing

The motion system is progressive enhancement: `clearglass-motion.css` carries a
static resting state for every animated construct, so a page is complete and
readable with the stylesheet present and JavaScript disabled. Both assets are
self-hosted, which the site's own Content-Security-Policy in `_headers`
requires (`script-src 'self'`).

Two scopes:

* Every page with a <head> gets the stylesheet and the deferred engine, so the
  glass, button and reveal vocabulary is shared site-wide.
* The homepage additionally gets the interface sections (hero growth interface,
  capability constellation, four-scene narrative). These are inserted *before*
  the generated `cg-related` block and never replace existing markup — the
  working video hero is left intact.

Everything this script writes is delimited by cgm-motion markers and is rewritten
in place on re-run, so it is safe to run repeatedly and trivial to revert.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CSS_HREF = "/clearglass-motion.css"
JS_SRC = "/clearglass-motion.js"

HEAD_START = "<!-- cgm-motion:head:start -->"
HEAD_END = "<!-- cgm-motion:head:end -->"
BODY_START = "<!-- cgm-motion:body:start -->"
BODY_END = "<!-- cgm-motion:body:end -->"
MAIN_START = "<!-- cgm-motion:sections:start -->"
MAIN_END = "<!-- cgm-motion:sections:end -->"

# Directories that are not part of the deployable site.
SKIP_PARTS = {
    ".git", "node_modules", "archive", "internal", "operations",
    "provenance", "downloads", "audit_logs", "__pycache__",
}

HEAD_BLOCK = f"""{HEAD_START}
<link rel="stylesheet" href="{CSS_HREF}">
{HEAD_END}"""

BODY_BLOCK = f"""{BODY_START}
<div class="cgm-atmos" aria-hidden="true">
  <div class="cgm-atmos__field cgm-atmos__field--signal"></div>
  <div class="cgm-atmos__field cgm-atmos__field--wine"></div>
  <div class="cgm-atmos__grid"></div>
  <div class="cgm-atmos__scan"></div>
  <div class="cgm-atmos__cursor"></div>
  <div class="cgm-atmos__noise"></div>
</div>
<div class="cgm-cursor" aria-hidden="true"></div>
<button type="button" class="cgm-motion-toggle" data-cgm-motion-toggle data-no-future-glass aria-pressed="false">Reduce visual effects</button>
{BODY_END}"""

TAIL_BLOCK = f"""<!-- cgm-motion:tail:start -->
<script defer src="{JS_SRC}"></script>
<!-- cgm-motion:tail:end -->"""

HERO_NODES = [
    ("Attention", "Being seen by the right people, in the places they already look."),
    ("Trust", "Evidence, provenance and clarity that let a stranger believe you."),
    ("Conversion", "Turning understanding into a booked, qualified conversation."),
    ("Performance", "Speed and stability, because neither trust nor ranking survives a slow page."),
    ("Search", "Technical discoverability: structure, schema and internal authority."),
    ("Automation", "Governed workflows that remove manual steps, not human approval."),
    ("Security", "Header posture, dependency integrity and an auditable trail."),
    ("Learning", "Measurement that closes the loop and improves the next cycle."),
]

SERVICES = [
    ("Digital strategy", "Positioning and sequencing — deciding what to build before building it."),
    ("Web design & development", "Interface, narrative and a typed, accessible, maintainable build."),
    ("AI automation", "Model-assisted workflows under read-only analysis, draft, approval, log."),
    ("Cybersecurity", "Threat modelling, edge posture and evidence an auditor accepts."),
    ("DevSecOps", "Pipelines that gate on tests and policy rather than on good intentions."),
    ("SEO & discoverability", "Structure, schema and link authority that compound over quarters."),
    ("Data integration", "Contracts between systems, validated at the boundary."),
    ("Growth infrastructure", "The connective layer that makes the rest measurable."),
]

SCENES = [
    ("01", "Fragmentation", "Most digital systems are built in fragments.",
     ["Website", "Content", "Data", "Leads", "Automation", "Security", "Analytics"], True),
    ("02", "Architecture", "ClearGlass connects the pieces into a system.",
     ["Strategy", "Experience", "Infrastructure", "Measurement", "Optimization"], False),
    ("03", "Activation", "Every interaction becomes a measurable opportunity to improve.",
     ["Discover", "Engage", "Convert", "Learn", "Improve"], False),
    ("04", "Growth infrastructure",
     "Your website becomes more than a destination. It becomes growth infrastructure.",
     ["Build the system"], False),
]


def _hero_section() -> str:
    nodes = "\n".join(
        f'      <li class="cgm-glass cgm-hero-node" data-cgm-reveal data-cgm-group="hero">'
        f'<h3>{label}</h3><p>{copy}</p></li>'
        for label, copy in HERO_NODES
    )
    return f"""<section class="cgm-scene" aria-labelledby="cgm-hero-interface-h">
  <div class="cgm-shell">
    <p class="cgm-eyebrow">Growth Infrastructure Interface</p>
    <h2 id="cgm-hero-interface-h" class="cgm-display" data-cgm-reveal>Build a digital system that compounds attention, trust, and growth.</h2>
    <p class="cgm-lede" data-cgm-reveal>ClearGlass Inc. designs high-performance websites and intelligent digital systems that connect strategy, engineering, automation, discoverability, analytics, and security-conscious architecture.</p>
    <p class="cgm-actions" data-cgm-reveal>
      <a class="cgm-btn" data-cgm-magnetic href="store.html">Engineer my growth system <span class="cgm-btn__arrow" aria-hidden="true">&rarr;</span></a>
      <a class="cgm-btn cgm-btn--secondary" href="#cgm-constellation-h">Explore the system</a>
    </p>
    <ul class="cgm-hero-nodes">
{nodes}
    </ul>
    <p class="cgm-illustrative">Interactive demonstration — illustrative data only.</p>
  </div>
</section>"""


def _constellation_section() -> str:
    return """<section class="cgm-scene" aria-labelledby="cgm-constellation-h" data-cgm-constellation>
  <div class="cgm-shell">
    <p class="cgm-eyebrow">Capability constellation</p>
    <h2 id="cgm-constellation-h" class="cgm-display" data-cgm-reveal>Nine capabilities, one system.</h2>
    <p class="cgm-lede" data-cgm-reveal>Select two or more capabilities to trace an engagement pathway. Every node is keyboard reachable and carries its own written explanation.</p>
    <div class="cgm-constellation" data-cgm-reveal>
      <div class="cgm-constellation__stage" data-no-future-glass></div>
      <div class="cgm-constellation__readout">
        <h3 data-cgm-readout-title>Operations</h3>
        <p data-cgm-readout-body>The connective layer: runbooks, ownership, escalation and the boring reliability work that compounds.</p>
        <p class="cgm-constellation__pathway" data-cgm-pathway hidden></p>
        <p class="cgm-illustrative">Interactive demonstration — illustrative data only.</p>
      </div>
    </div>
  </div>
</section>"""


def _services_section() -> str:
    cards = "\n".join(
        f'      <li class="cgm-glass cgm-trace cgm-tilt cgm-service" data-cgm-reveal data-cgm-group="svc">'
        f'<h3>{name}</h3><p>{copy}</p></li>'
        for name, copy in SERVICES
    )
    return f"""<section class="cgm-scene" aria-labelledby="cgm-services-h">
  <div class="cgm-shell">
    <p class="cgm-eyebrow">Capabilities</p>
    <h2 id="cgm-services-h" class="cgm-display" data-cgm-reveal>What we build.</h2>
    <ul class="cgm-services">
{cards}
    </ul>
  </div>
</section>"""


def _narrative_sections() -> str:
    out = []
    for num, title, copy, items, scatter in SCENES:
        cls = "cgm-scene cgm-scene--scatter" if scatter else "cgm-scene"
        slug = f"cgm-scene-{num}"
        if num == "04":
            inner = (
                '      <p class="cgm-actions" data-cgm-reveal>'
                '<a class="cgm-btn" data-cgm-magnetic href="store.html">Build the system '
                '<span class="cgm-btn__arrow" aria-hidden="true">&rarr;</span></a></p>'
            )
        else:
            frags = "\n".join(
                f'        <li class="cgm-scene__frag">{item}</li>' for item in items
            )
            inner = f'      <ul class="cgm-scene__frags" data-cgm-reveal>\n{frags}\n      </ul>'
        out.append(
            f"""<section class="{cls}" aria-labelledby="{slug}-h" data-cgm-reveal>
  <div class="cgm-shell">
    <p class="cgm-eyebrow">Scene {num} — {title}</p>
    <h2 id="{slug}-h" class="cgm-display">{copy}</h2>
{inner}
  </div>
</section>"""
        )
    return "\n".join(out)


SECTIONS_BLOCK = (
    f"{MAIN_START}\n"
    '<div class="cgm-motion-sections">\n'
    f"{_hero_section()}\n"
    f"{_constellation_section()}\n"
    f"{_services_section()}\n"
    f"{_narrative_sections()}\n"
    "</div>\n"
    f"{MAIN_END}"
)


def _replace_block(text: str, start: str, end: str, block: str) -> str:
    """Rewrite an existing delimited block, or return text unchanged."""
    if start not in text:
        return text
    head, _, rest = text.partition(start)
    _, _, tail = rest.partition(end)
    return head + block + tail


def apply_to(path: Path, homepage: bool) -> bool:
    original = text = path.read_text(encoding="utf-8", errors="surrogateescape")

    if "</head>" not in text or "</body>" not in text:
        return False

    # ── stylesheet ────────────────────────────────────────────────────────
    if HEAD_START in text:
        text = _replace_block(text, HEAD_START, HEAD_END, HEAD_BLOCK)
    else:
        text = text.replace("</head>", HEAD_BLOCK + "\n</head>", 1)

    # ── atmosphere / cursor / preference control ──────────────────────────
    if BODY_START in text:
        text = _replace_block(text, BODY_START, BODY_END, BODY_BLOCK)
    else:
        marker = "<body>"
        at = text.find(marker)
        if at == -1:                      # <body class="..."> and friends
            at = text.find("<body")
            if at == -1:
                return False
            close = text.find(">", at)
            if close == -1:
                return False
            insert_at = close + 1
        else:
            insert_at = at + len(marker)
        text = text[:insert_at] + "\n" + BODY_BLOCK + text[insert_at:]

    # ── homepage interface sections ───────────────────────────────────────
    if homepage:
        if MAIN_START in text:
            text = _replace_block(text, MAIN_START, MAIN_END, SECTIONS_BLOCK)
        else:
            anchor = "<!-- cg-related:start -->"
            if anchor in text:
                text = text.replace(anchor, SECTIONS_BLOCK + "\n" + anchor, 1)
            else:
                text = text.replace("</body>", SECTIONS_BLOCK + "\n</body>", 1)

    # ── engine, last so it sees final markup ──────────────────────────────
    if "cgm-motion:tail:start" in text:
        text = _replace_block(text, "<!-- cgm-motion:tail:start -->",
                              "<!-- cgm-motion:tail:end -->", TAIL_BLOCK)
    else:
        text = text.replace("</body>", TAIL_BLOCK + "\n</body>", 1)

    if text == original:
        return False
    path.write_text(text, encoding="utf-8", errors="surrogateescape")
    return True


def deployable_pages() -> list[Path]:
    pages = []
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        pages.append(path)
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if any page is missing the motion layer")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    parser.add_argument("--homepage-only", action="store_true",
                        help="only touch index.html")
    args = parser.parse_args()

    pages = [ROOT / "index.html"] if args.homepage_only else deployable_pages()
    stale: list[str] = []
    changed: list[str] = []

    for path in pages:
        rel = str(path.relative_to(ROOT))
        homepage = rel == "index.html"
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        if "</head>" not in text or "</body>" not in text:
            continue

        needs = (HEAD_START not in text
                 or BODY_START not in text
                 or "cgm-motion:tail:start" not in text
                 or (homepage and MAIN_START not in text))

        if args.check:
            if needs:
                stale.append(rel)
            continue
        if args.dry_run:
            if needs:
                changed.append(rel)
            continue
        if apply_to(path, homepage):
            changed.append(rel)

    if args.check:
        if stale:
            print(f"stale: {len(stale)} page(s) missing the motion layer")
            for rel in stale[:20]:
                print(f"  {rel}")
            return 1
        print(f"ok: motion layer present on {len(pages)} page(s)")
        return 0

    verb = "would update" if args.dry_run else "updated"
    print(f"{verb} {len(changed)} of {len(pages)} page(s)")
    for rel in changed[:20]:
        print(f"  {rel}")
    if len(changed) > 20:
        print(f"  … and {len(changed) - 20} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
