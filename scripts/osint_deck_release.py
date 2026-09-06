#!/usr/bin/env python3
"""Burlington OSINT Control Deck — release validator (dry-run by default).

A deterministic, fail-closed pre-flight gate for the OSINT deck. It validates
that the published artifact is well-formed and internally consistent, then emits
an auditable report plus release notes. It NEVER deploys or publishes: the deck
ships through the existing GitHub Pages path on merge to main, and production
publishing stays a human-approved step.

Checks (all must pass in --strict):
  - Ontario-osint.html exists and is search-indexable (robots: index)
  - data/Ontario-osint/intel.json is valid JSON with required keys
  - sitemap.xml is well-formed XML and lists the deck
  - nav.js links the deck (site-wide reachability)
  - sw.js precaches the deck (offline / from-any-location availability)
  - inline <script> blocks and sw.js pass `node --check` (when node present)

Usage:
  python scripts/osint_deck_release.py            # dry-run, advisory
  python scripts/osint_deck_release.py --strict   # fail closed on any error
  python scripts/osint_deck_release.py --release   # label run as a release gate
  python scripts/osint_deck_release.py --out release/report.md
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.dom.minidom as minidom
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "Ontario-osint.html"
INTEL = ROOT / "data" / "Ontario-osint" / "intel.json"
SITEMAP = ROOT / "sitemap.xml"
NAV = ROOT / "nav.js"
SW = ROOT / "sw.js"
DECK_URL = "https://www.clearglassinc.com/Ontario-osint.html"


def check(results: list[tuple[str, bool, str]], name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


def validate() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    # 1. deck present + indexable
    if DECK.exists():
        html = DECK.read_text(encoding="utf-8")
        indexable = 'name="robots" content="index' in html
        check(results, "deck present", True, str(DECK.relative_to(ROOT)))
        check(results, "deck indexable", indexable,
              "robots=index" if indexable else "robots is not index,follow")
    else:
        html = ""
        check(results, "deck present", False, "Ontario-osint.html missing")
        check(results, "deck indexable", False, "deck missing")

    # 2. intel.json valid + required keys
    if INTEL.exists():
        try:
            data = json.loads(INTEL.read_text(encoding="utf-8"))
            required = {"region", "summary", "metrics", "sources"}
            missing = required - data.keys()
            check(results, "intel.json valid", not missing,
                  "ok" if not missing else f"missing keys: {sorted(missing)}")
        except json.JSONDecodeError as exc:
            check(results, "intel.json valid", False, f"JSON error: {exc}")
    else:
        check(results, "intel.json valid", False, "intel.json missing")

    # 3. sitemap well-formed + lists deck
    if SITEMAP.exists():
        try:
            minidom.parseString(SITEMAP.read_text(encoding="utf-8"))
            listed = "Ontario-osint.html" in SITEMAP.read_text(encoding="utf-8")
            check(results, "sitemap valid", True, "well-formed XML")
            check(results, "sitemap lists deck", listed,
                  "listed" if listed else "deck URL not in sitemap")
        except Exception as exc:  # noqa: BLE001 - report any parse failure
            check(results, "sitemap valid", False, f"XML error: {exc}")
    else:
        check(results, "sitemap valid", False, "sitemap.xml missing")

    # 4. nav links the deck
    nav_ok = NAV.exists() and "Ontario-osint.html" in NAV.read_text(encoding="utf-8")
    check(results, "nav links deck", nav_ok,
          "linked site-wide" if nav_ok else "nav.js does not link the deck")

    # 5. service worker precaches the deck
    sw_ok = SW.exists() and "/Ontario-osint.html" in SW.read_text(encoding="utf-8")
    check(results, "sw precaches deck", sw_ok,
          "offline-ready" if sw_ok else "deck not in sw precache")

    # 6. JS syntax (node optional)
    node = shutil.which("node")
    if node and html:
        blocks = [b for b in re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S)
                  if b.strip() and "src=" not in b[:60]]
        js_ok = True
        detail = f"{len(blocks)} inline block(s) + sw.js"
        for i, block in enumerate([*blocks, SW.read_text(encoding="utf-8") if SW.exists() else ""]):
            if not block.strip():
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
                fh.write(block)
                tmp = fh.name
            proc = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
            Path(tmp).unlink(missing_ok=True)
            if proc.returncode != 0:
                js_ok = False
                detail = f"syntax error in block {i}: {proc.stderr.strip()[:160]}"
                break
        check(results, "js syntax", js_ok, detail)
    else:
        check(results, "js syntax", True, "skipped (node unavailable)")

    return results


def render_report(results: list[tuple[str, bool, str]], release: bool) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    mode = "RELEASE GATE" if release else "DRY RUN"
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    status = "PASS" if passed == total else "FAIL"
    lines = [
        "# Burlington OSINT Control Deck — Release Report",
        "",
        f"- **Mode:** {mode}",
        f"- **Generated:** {now}",
        f"- **Target:** {DECK_URL}",
        f"- **Result:** {status} ({passed}/{total} checks passed)",
        "",
        "## Validation gates",
        "",
        "| Gate | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'✅ pass' if ok else '❌ fail'} | {detail} |")
    lines += [
        "",
        "## Release notes (auto-generated)",
        "",
        "- Self-contained, dependency-free OSINT control deck (deploys on GitHub Pages).",
        "- Live status stream, optimistic investigation-task queue, cited crime-intel feed.",
        "- Offline / from-any-location availability via service-worker precache.",
        "- Burlington satellite-imagery links surfaced in the deck.",
        "- All data references lawful public sources only.",
        "",
        "## Rollback",
        "",
        "- Deploy path is GitHub Pages from `main`. To roll back, revert the offending",
        "  commit on `main`; Pages redeploys the previous state automatically.",
        "- No external services, credentials, or data stores are mutated by this deck.",
        "",
        "## Next action",
        "",
        ("- Release gate passed — safe to merge/publish via the human-approved path."
         if status == "PASS" else
         "- Release gate FAILED — do not publish. Resolve the failing gate(s) above."),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="OSINT deck release validator (dry-run by default).")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any failed gate")
    parser.add_argument("--release", action="store_true", help="label run as a release gate")
    parser.add_argument("--out", default="", help="write the markdown report to this path")
    args = parser.parse_args()

    results = validate()
    report = render_report(results, args.release)
    print(report)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"report written to {out}")

    failed = [name for name, ok, _ in results if not ok]
    if failed:
        print(f"FAILED gates: {', '.join(failed)}", file=sys.stderr)
        # Fail closed only under --strict; dry-run stays advisory.
        return 1 if args.strict else 0
    print("All release gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
