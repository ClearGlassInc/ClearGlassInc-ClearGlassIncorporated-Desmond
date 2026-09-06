# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#!/usr/bin/env python3
"""Backward-compatible entrypoint for site integrity checks.

This wrapper preserves older workflow references to ``scripts/site_integrity.py``
while delegating to the canonical reliability audit implementation.
"""

from __future__ import annotations

from site_reliability_audit import main


if __name__ == "__main__":
    raise SystemExit(main())
