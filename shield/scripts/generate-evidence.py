#!/usr/bin/env python3
"""Build G01 evidence from a run's records. See shield/evidence.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shield.evidence import main  # noqa: E402

raise SystemExit(main(sys.argv[1:]))
