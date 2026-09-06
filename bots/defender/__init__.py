# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass Defender — a 3-layer defensive security orchestrator.

    Sensor layer   → engine.scan_workflows / scan_secrets / scan_dependencies /
                     scan_commands  (emit structured Findings)
    Policy layer   → policy.load_policy / classify / response_plan
                     (severity, allowlist, graded response from one JSON policy)
    Response layer → alerting.dispatch  +  quarantine.quarantine
                     (non-destructive: alert and flag-for-review, never delete)

Entry points consumed by scripts/bot_runner.py and `python -m bots.defender`:

    run()  -> dict   full scan + response; returns a manifest, never raises on
                     findings (so it is safe inside the bot orchestrator).
    main() -> None   CLI wrapper; exits non-zero per policy.enforcement.fail_build_on
                     (used as the gate in the defender-watch workflow).
"""
from __future__ import annotations

from bots.defender.engine import main, run

__all__ = ["run", "main"]
