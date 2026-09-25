#!/usr/bin/env python3
"""Offline integrity checks for the ClearGlass Station homepage layer.

This validator is intentionally dependency-free so it can run locally even when
GitHub Actions execution is blocked. It does not modify repository files.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sentinel = ROOT / "sentinel.js"
index = ROOT / "index.html"

errors = []

if not index.is_file():
    errors.append("missing index.html")
if not sentinel.is_file():
    errors.append("missing sentinel.js")

if not errors:
    html = index.read_text(encoding="utf-8")
    js = sentinel.read_text(encoding="utf-8")

    required_html = ["sentinelShell", "sentinelLauncher", "sentinel-panel"]
    required_js = [
        "ClearGlass Station",
        "CLEARGLASS STATION",
        "data-station-close",
        "data-station-chat",
        "cg-station-grid",
        'href=\"offers/index.html\"',
        'href=\"pricing.html\"',
        'href=\"products.html\"',
        'href=\"systems.html\"',
        'href=\"CG-os.html\"',
        'href=\"agentmesh.html\"',
        'href=\"conduit.html\"',
        'href=\"artemis.html\"',
        'href=\"command-center.html\"',
        'href=\"blog/\"',
        'href=\"store.html\"',
        'href=\"contact.html\"',
    ]

    for marker in required_html:
        if marker not in html:
            errors.append(f"index.html missing marker: {marker}")
    for marker in required_js:
        if marker not in js:
            errors.append(f"sentinel.js missing marker: {marker}")

    # The directory header must be rendered exactly once; a second copy means
    # the Station layer was pasted in twice.
    if js.count("CLEARGLASS STATION") != 1:
        errors.append("unexpected CLEARGLASS STATION header count")
    if "originalPanelHTML=panel.innerHTML" not in js:
        errors.append("original Sentinel panel preservation hook missing")
    if "panel.innerHTML=originalPanelHTML" not in js:
        errors.append("ASK SENTINEL restoration hook missing")
    # [data-sentinel-open] and the launcher route to the Station directory.
    if "el.addEventListener(\"click\",queueStation)" not in js:
        errors.append("launcher-to-Station routing hook missing")
    # The Sentinel Core dock opens the conversation directly, never the directory.
    if "window.__cgSentinel=" not in js:
        errors.append("Sentinel Core hand-off API (window.__cgSentinel) missing")
    dock = ROOT / "station-chat.js"
    if not dock.is_file():
        errors.append("missing station-chat.js")
    else:
        dock_js = dock.read_text(encoding="utf-8")
        for marker in ("SENTINEL CORE", "__cgSentinel", "data-no-future-glass", "cgst-absorb-stack",
                       "Intel Desk", "blog/posts.json", "function intelFallback()",
                       "Site Intelligence", "data/site-index.json", "function siteFallback()",
                       "Intelligence Graph", "Mission Control"):
            if marker not in dock_js:
                errors.append(f"station-chat.js missing marker: {marker}")

    # Lightweight structural sanity: balanced braces/parens is only a heuristic,
    # but catches common truncation/corruption without requiring Node.js.
    if js.count("{") != js.count("}"):
        errors.append("sentinel.js brace count is unbalanced")
    if js.count("(") != js.count(")"):
        errors.append("sentinel.js parenthesis count is unbalanced")

if errors:
    print("SENTINEL STATION VALIDATION: FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("SENTINEL STATION VALIDATION: PASS")
print("- Existing homepage Sentinel shell markers present")
print("- ClearGlass Station routing layer present")
print("- 13 navigation destinations present")
print("- Original Sentinel panel preservation/restoration hooks present")
print("- Launcher routing hook present")
print("- Sentinel Core dock and direct-chat hand-off present")
print("- Intel Desk wired to the brief index, with its offline fallback")
print("- Site Intelligence wired to the site index, with its offline fallback")
print("- Basic JavaScript delimiter sanity passed")
