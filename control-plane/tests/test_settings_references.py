"""Every setting the app reads must exist on ``Settings``.

The CRCS router (0cfcfff) shipped reading five settings that ``Settings`` never
defined. Reading an undefined field raises ``AttributeError``, so
``POST /revenue/leads`` answered every request, valid or not, with a 500 before
its handler ran, and ``/revenue/public-offer`` and ``/revenue/checkout`` would
have done the same on their first valid call. The CRCS tests exercised scoring
only and never touched a route, so nothing caught it. The intended values sat
in ``.env.example`` the whole time; only the ``Settings`` fields were missing.

This reads source text, so it needs no database and no running app.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"

try:
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.config import Settings
except ImportError:  # pragma: no cover - minimal env runs pure tests only
    Settings = None

#: Attribute reads such as ``settings.crcs_first_offer_sku``.
ATTRIBUTE = re.compile(r"\bsettings\.([a-z_][a-z0-9_]*)")
#: ``rate_limit("bucket", "<setting>")`` names its setting as a string, which an
#: attribute check cannot see. That is how ``revenue_lead_rate_limit_per_minute``
#: went missing.
RATE_LIMIT_SETTING = re.compile(r'rate_limit\(\s*"[a-z_]+"\s*,\s*"([a-z_]+)"\s*\)')


def _reads() -> dict[str, set[str]]:
    reads = {}
    for path in sorted(APP.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        used = set(ATTRIBUTE.findall(text)) | set(RATE_LIMIT_SETTING.findall(text))
        if used:
            reads[str(path.relative_to(APP.parent))] = used
    return reads


def test_every_setting_the_app_reads_is_defined() -> None:
    if Settings is None:
        pytest.skip("pydantic-settings not installed")
    defined = set(Settings.model_fields)
    undefined = {
        path: sorted(name for name in used if name not in defined and not name.startswith("model_"))
        for path, used in _reads().items()
    }
    undefined = {path: names for path, names in undefined.items() if names}
    assert not undefined, (
        f"These modules read settings that Settings does not define: {undefined}. "
        f"Each read raises AttributeError at request time, not at startup. Add the "
        f"field to app/config.py, with the default .env.example documents."
    )


def test_the_scan_actually_finds_settings_reads() -> None:
    """Guard the guard: a regex that matched nothing would pass vacuously."""
    reads = _reads()
    assert sum(len(used) for used in reads.values()) > 20, reads
    assert "revenue_lead_rate_limit_per_minute" in reads.get("app/routers/revenue.py", set())
