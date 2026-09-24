"""What the control plane refuses, or warns about, before it serves a request.

The fail-closed start without ``ADMIN_API_KEY`` in production is the reason an
unauthenticated admin surface cannot ship; until now only a manual run checked
it. ``CRCS_AUDIT_HASH_KEY`` falls back to a constant in this repository, which
turns the ledger's buyer pseudonyms into something anyone can recompute, so a
production start without it is logged.
"""
from __future__ import annotations

import logging
import os

import pytest

try:
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.config import Settings
    from app.security import verify_startup_posture

    _HAS_SETTINGS = True
except ImportError:  # pragma: no cover - minimal env runs pure tests only
    _HAS_SETTINGS = False

pytestmark = pytest.mark.skipif(not _HAS_SETTINGS, reason="pydantic-settings not installed")

HASH_WARNING = "CRCS_AUDIT_HASH_KEY is not set"


def _settings(**overrides) -> Settings:
    base = {"app_env": "production", "admin_api_key": "k" * 32, "crcs_audit_hash_key": "h" * 32}
    return Settings(_env_file=None, **{**base, **overrides})


def test_production_without_admin_key_refuses_to_start() -> None:
    with pytest.raises(RuntimeError, match="ADMIN_API_KEY"):
        verify_startup_posture(_settings(admin_api_key=""))


def test_production_without_audit_hash_key_is_logged(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="clearglass.security"):
        verify_startup_posture(_settings(crcs_audit_hash_key=""))
    assert HASH_WARNING in caplog.text


def test_fully_configured_production_starts_quietly(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="clearglass.security"):
        verify_startup_posture(_settings())
    assert HASH_WARNING not in caplog.text


def test_development_does_not_nag_about_the_hash_key(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="clearglass.security"):
        verify_startup_posture(_settings(app_env="development", crcs_audit_hash_key=""))
    assert HASH_WARNING not in caplog.text
