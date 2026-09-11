#!/usr/bin/env python3
"""Reproduce ci.yml's "Validate generated search assets are current" step.

That step is two commands, and the second is what actually gates:

    python3 tools/generate_search_assets.py
    git diff --exit-code -- sitemap.xml feed.xml data/seo/page-intents.json

Running the generator always succeeds; the failure is *drift* between the
committed assets and what the generator produces. ``scripts/ci_local.py``
invokes single commands, so the pair lives here.

This writes to the working tree, exactly as CI does. On failure the drift is
left in place so it can be inspected and committed - that is the fix.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ["sitemap.xml", "feed.xml", "data/seo/page-intents.json"]


def main() -> int:
    generate = subprocess.run(
        [sys.executable, "tools/generate_search_assets.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if generate.returncode != 0:
        sys.stderr.write(generate.stdout + generate.stderr)
        return generate.returncode

    drift = subprocess.run(
        ["git", "diff", "--exit-code", "--", *GENERATED],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if drift.returncode == 0:
        print(f"search assets current: {', '.join(GENERATED)}")
        return 0

    stat = subprocess.run(
        ["git", "diff", "--stat", "--", *GENERATED],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    sys.stderr.write(
        "generated search assets are stale; the generator produced different "
        "output than what is committed:\n" + stat.stdout +
        "\nRe-run tools/generate_search_assets.py and commit the result.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
