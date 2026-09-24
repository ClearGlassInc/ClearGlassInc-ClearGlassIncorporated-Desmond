"""Fail, don't skip, when FastAPI is installed but its TestClient cannot load.

Six test modules, ``test_route_auth_coverage.py`` among them, set
``_HAS_WEB_STACK = False`` and skip when ``fastapi.testclient`` will not
import. That is right for a minimal environment with no FastAPI at all. It is
wrong when FastAPI is present and only the client library is missing: the
access-control gate then passes by skipping. Starlette 1.7 already warns that
``httpx`` is deprecated for its TestClient in favour of ``httpx2`` and raises
``RuntimeError`` when neither is installed, so a dependency bump alone could
turn those gates off without a red test.
"""
from __future__ import annotations

import importlib.util
import warnings

import pytest


def test_testclient_imports_wherever_fastapi_does() -> None:
    if importlib.util.find_spec("fastapi") is None:
        pytest.skip("fastapi not installed: the web-stack tests are meant to skip here")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from fastapi.testclient import TestClient  # noqa: F401
    except (ImportError, RuntimeError) as exc:
        pytest.fail(
            "fastapi is installed but fastapi.testclient does not import "
            f"({type(exc).__name__}: {exc}). Every route test, including "
            "test_route_auth_coverage.py, is skipping. Install the HTTP client "
            "Starlette asks for (control-plane/requirements.txt)."
        )
