"""Make the control-plane package importable when running tests locally."""
from __future__ import annotations

import sys
from pathlib import Path

CONTROL_PLANE = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE))
