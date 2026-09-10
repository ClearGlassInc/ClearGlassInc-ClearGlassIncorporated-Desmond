# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.cert_bot import (
    CertResult,
    annotate,
    days_until,
    evaluate_host,
    parse_hosts,
    parse_not_after,
    run,
)

NOW = datetime(2026, 6, 5, tzinfo=timezone.utc)


# ── parse_hosts ───────────────────────────────────────────────────────────────

def test_parse_hosts_basic():
    assert parse_hosts("www.clearglassinc.com") == ["www.clearglassinc.com"]


def test_parse_hosts_strips_scheme_port_path_and_blanks():
    raw = "https://www.clearglassinc.com/path, www.clearglassinc.com:443 , ,api.clearglassinc.com"
    assert parse_hosts(raw) == [
        "www.clearglassinc.com",
        "www.clearglassinc.com",
        "api.clearglassinc.com",
    ]


def test_parse_hosts_empty():
    assert parse_hosts("   ,  ") == []


# ── parse_not_after / days_until ──────────────────────────────────────────────

def test_parse_not_after_openssl_format():
    parsed = parse_not_after("Jun  5 12:00:00 2027 GMT")
    assert parsed == datetime(2027, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_days_until_future_and_past():
    assert days_until(NOW + timedelta(days=30), NOW) == 30
    assert days_until(NOW - timedelta(days=2), NOW) == -2


# ── evaluate_host ─────────────────────────────────────────────────────────────

def _fetcher_at(days: int):
    def _fetch(host, port, timeout):
        return NOW + timedelta(days=days)
    return _fetch


def test_evaluate_host_healthy():
    result = evaluate_host("example.com", 21, NOW, fetcher=_fetcher_at(60))
    assert result.ok
    assert result.days_left == 60


def test_evaluate_host_captures_errors():
    def _boom(host, port, timeout):
        raise OSError("connection refused")

    result = evaluate_host("example.com", 21, NOW, fetcher=_boom)
    assert not result.ok
    assert "connection refused" in (result.error or "")


# ── annotate ──────────────────────────────────────────────────────────────────

def test_annotate_expiring_is_failure():
    result = CertResult(host="h", days_left=5, expiry=NOW + timedelta(days=5))
    line, failed = annotate(result, 21, strict=True)
    assert failed
    assert "::error" in line and "expires in 5" in line


def test_annotate_healthy_is_not_failure():
    result = CertResult(host="h", days_left=40, expiry=NOW + timedelta(days=40))
    line, failed = annotate(result, 21, strict=True)
    assert not failed
    assert "::notice" in line


def test_annotate_unreachable_respects_strict_flag():
    result = CertResult(host="h", error="timeout")
    strict_line, strict_failed = annotate(result, 21, strict=True)
    soft_line, soft_failed = annotate(result, 21, strict=False)
    assert strict_failed and "::error" in strict_line
    assert not soft_failed and "::warning" in soft_line


def test_annotate_auto_managed_expiring_is_advisory():
    # *.github.io auto-renews: a still-valid but soon cert warns, never fails.
    result = CertResult(host="clearglassinc.github.io", days_left=19,
                        expiry=NOW + timedelta(days=19))
    line, failed = annotate(result, 21, strict=True)
    assert not failed
    assert "::warning" in line and "auto-renews" in line


def test_annotate_auto_managed_expired_still_fails():
    # An actually-expired managed cert is a real outage and still errors.
    result = CertResult(host="clearglassinc.github.io", days_left=-1,
                        expiry=NOW - timedelta(days=1))
    line, failed = annotate(result, 21, strict=True)
    assert failed and "::error" in line


# ── run ───────────────────────────────────────────────────────────────────────

def test_run_returns_zero_when_all_healthy():
    code = run(["a.com", "b.com"], 21, strict=True, now=NOW, fetcher=_fetcher_at(45))
    assert code == 0


def test_run_returns_one_when_any_expiring():
    code = run(["a.com"], 21, strict=True, now=NOW, fetcher=_fetcher_at(3))
    assert code == 1


def test_run_with_no_hosts_fails():
    assert run([], 21, strict=True, now=NOW) == 1
