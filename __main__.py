# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""CLI entrypoint: ``python -m agent_os``.

Runs an end-to-end governed demo mission and prints the mission report as JSON.
Delegates to the self-check so there is a single source of truth for the demo.
"""
from __future__ import annotations

import json

from .self_check import demo_mission, governance_selfcheck


def main(argv: list[str] | None = None) -> int:
    failures = governance_selfcheck()
    if failures:
        print(json.dumps({"status": "FAIL", "failures": failures}, indent=2))
        return 1
    print(json.dumps({"status": "OK", "mission": demo_mission()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
