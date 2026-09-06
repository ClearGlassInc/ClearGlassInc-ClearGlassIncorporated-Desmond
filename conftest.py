# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Repository-wide pytest import path setup for monorepo test runs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMPORT_ROOTS = (
    ROOT,
    ROOT / "sentinel",
    ROOT / "clearglass-commerce" / "control-plane",
)

for import_root in IMPORT_ROOTS:
    import_root_str = str(import_root)
    if import_root_str not in sys.path:
        sys.path.insert(0, import_root_str)
