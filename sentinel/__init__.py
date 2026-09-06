# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Compatibility package for running Sentinel from the monorepo root.

The implementation package lives in ``sentinel/sentinel``.  Extending
``__path__`` lets imports such as ``sentinel.policy`` work both when tests are
run from ``sentinel/`` and when the entire monorepo is tested from the root.
"""
from __future__ import annotations

from pathlib import Path

_IMPL = Path(__file__).resolve().parent / "sentinel"
if str(_IMPL) not in __path__:
    __path__.append(str(_IMPL))
