from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import pytest

from scripts.strait_watch import (
    ValidationError,
    fingerprint,
    load_registry,
    load_state,
    normalize_content,
    save_state,
    signed_webhook_body,
)


def test_html_normalization_ignores_script_and_whitespace() -> None:
    first = b"""<html><body><h1>Alpha</h1><script>volatile()</script><p>Beta</p></body></html>"""
    second = b"""<html><body> <h1>Alpha</h1> <script>different()</script> <p>Beta</p> </body></html>"""
    a = normalize_content(first, "text/html")
    b = normalize_content(second, "text/html")
    assert a == "Alpha Beta"
    assert a == b
    assert fingerprint(a) == fingerprint(b)


def test_json_normalization_is_key_order_independent() -> None:
    first = normalize_content(b'{"b":2,"a":1}', "application/json")
    second = normalize_content(b'{"a":1,"b":2}', "application/json")
    assert first == second == '{"a":1,"b":2}'


def test_json_invalid_payload_fails_closed() -> None:
    with pytest.raises(ValidationError):
        normalize_content(b"not-json", "application/json")


def test_registry_is_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    policy, sources = load_registry(root / "data/strait-watch/sources.json")
    assert policy["version"] == "1.0"
    assert len(sources) >= 5
    assert all(source.url.startswith("https://") for source in sources)


def test_registry_rejects_http_and_non_allowlisted_host(tmp_path: Path) -> None:
    bad = {
        "version": "1.0",
        "sources": [
            {
                "id": "bad",
                "authority": "Example",
                "url": "http://example.com/",
                "allowed_hosts": ["example.com"],
                "content_types": ["text/html"],
            }
        ],
    }
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValidationError, match="HTTPS"):
        load_registry(path)


def test_state_round_trip_uses_durable_json(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    expected = {"version": 1, "sources": {"x": {"sha256": "abc"}}}
    save_state(path, expected)
    assert load_state(path) == expected


def test_signed_webhook_body_has_verifiable_hmac() -> None:
    payload = {"event": "strait_watch_change", "source_id": "cnsc-regulatory-documents"}
    body, signature = signed_webhook_body(payload, "test-secret")
    expected = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert signature == f"sha256={expected}"
