# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#!/usr/bin/env python3
"""Cert Bot — TLS certificate expiry monitor for ClearGlass endpoints.

Connects to each configured host over TLS, reads the leaf certificate's
``notAfter`` field, and fails if any certificate expires within a minimum
number of days. Designed to run as a scheduled GitHub Actions job ("track")
so a soon-to-expire certificate is surfaced long before it breaks the site.

Configuration (environment variables):
  CERT_BOT_HOSTS     Comma-separated hosts to check.
                     Default: "www.clearglassinc.com".
  CERT_BOT_MIN_DAYS  Minimum acceptable days until expiry. Default: 21.
  CERT_BOT_STRICT    If "1", an unreachable host is a failure. Default: "1".

Run locally:
  python scripts/cert_bot.py
  CERT_BOT_HOSTS="www.clearglassinc.com,www.clearglassinc.com" python scripts/cert_bot.py
"""

from __future__ import annotations

import os
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

DEFAULT_HOSTS = "www.clearglassinc.com"
DEFAULT_MIN_DAYS = 21
DEFAULT_PORT = 443
DEFAULT_TIMEOUT = 10.0

# Platform-managed domains issue and auto-renew their own TLS certificates, so a
# soon-to-expire (but still valid) cert is not actionable by this repo and should
# be advisory rather than a build failure. An already-expired one still errors.
# The primary site now serves from the GitHub Pages custom domain
# clearglassinc.com (and www), whose certificate GitHub provisions and renews
# automatically — so it is auto-managed just like the *.github.io Pages URL was.
AUTO_MANAGED_SUFFIXES = (".github.io", ".pages.dev", ".clearglassinc.com")
AUTO_MANAGED_HOSTS = ("clearglassinc.com",)


def is_auto_managed(host: str) -> bool:
    """True for platform-managed (auto-renewing) certificate hosts."""
    h = host.lower()
    return h.endswith(AUTO_MANAGED_SUFFIXES) or h in AUTO_MANAGED_HOSTS


@dataclass
class CertResult:
    """Outcome of a single host certificate check."""

    host: str
    days_left: int | None = None
    expiry: datetime | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def parse_hosts(raw: str) -> list[str]:
    """Split a comma-separated host list, stripping scheme/path and blanks."""
    hosts: list[str] = []
    for chunk in raw.split(","):
        token = chunk.strip()
        if not token:
            continue
        if "://" in token:
            token = urlparse(token).netloc or token
        token = token.split("/")[0].split(":")[0].strip()
        if token:
            hosts.append(token)
    return hosts


def parse_not_after(value: str) -> datetime:
    """Parse an OpenSSL ``notAfter`` string (e.g. 'Jun  5 12:00:00 2027 GMT')."""
    text = value.replace(" GMT", "").strip()
    parsed = datetime.strptime(text, "%b %d %H:%M:%S %Y")
    return parsed.replace(tzinfo=timezone.utc)


def days_until(expiry: datetime, now: datetime) -> int:
    """Whole days from ``now`` until ``expiry`` (negative if already expired)."""
    return (expiry - now).days


def fetch_not_after(
    host: str,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> datetime:  # pragma: no cover - network boundary
    """Open a TLS connection and return the leaf certificate's expiry (UTC)."""
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls:
            cert = tls.getpeercert()
    not_after = (cert or {}).get("notAfter")
    if not not_after:
        raise ValueError("certificate has no notAfter field")
    return parse_not_after(not_after)


def evaluate_host(
    host: str,
    min_days: int,
    now: datetime,
    fetcher=fetch_not_after,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> CertResult:
    """Check one host, returning a :class:`CertResult` (never raises)."""
    try:
        expiry = fetcher(host, port, timeout)
    except Exception as exc:  # noqa: BLE001 - report any failure as a result
        return CertResult(host=host, error=str(exc))
    return CertResult(host=host, days_left=days_until(expiry, now), expiry=expiry)


def annotate(result: CertResult, min_days: int, strict: bool) -> tuple[str, bool]:
    """Return a GitHub-annotated status line and whether it counts as a failure."""
    if result.error is not None:
        line = f"::{'error' if strict else 'warning'} title=Cert Bot::{result.host}: " \
               f"unreachable ({result.error})"
        return line, strict
    assert result.days_left is not None and result.expiry is not None
    stamp = result.expiry.date().isoformat()
    if result.days_left < min_days:
        # Platform-managed certs (e.g. *.github.io) auto-renew and aren't
        # actionable here: warn while still valid, only fail once expired.
        if is_auto_managed(result.host) and result.days_left >= 0:
            line = (
                f"::warning title=Cert Bot::{result.host}: certificate expires in "
                f"{result.days_left} day(s) on {stamp} (threshold {min_days}) — "
                f"platform-managed (auto-renews), advisory only"
            )
            return line, False
        line = (
            f"::error title=Cert Bot::{result.host}: certificate expires in "
            f"{result.days_left} day(s) on {stamp} (threshold {min_days})"
        )
        return line, True
    line = f"::notice title=Cert Bot::{result.host}: OK — {result.days_left} day(s) left ({stamp})"
    return line, False


def run(
    hosts: list[str],
    min_days: int,
    strict: bool,
    now: datetime | None = None,
    fetcher=fetch_not_after,
) -> int:
    """Evaluate every host and return a process exit code (0 = healthy)."""
    now = now or datetime.now(timezone.utc)
    if not hosts:
        print("::error title=Cert Bot::no hosts configured (set CERT_BOT_HOSTS)")
        return 1
    failures = 0
    for host in hosts:
        result = evaluate_host(host, min_days, now, fetcher=fetcher)
        line, failed = annotate(result, min_days, strict)
        print(line)
        failures += int(failed)
    print(f"Cert Bot checked {len(hosts)} host(s): {failures} failing, "
          f"{len(hosts) - failures} healthy.")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    hosts = parse_hosts(os.environ.get("CERT_BOT_HOSTS", DEFAULT_HOSTS))
    try:
        min_days = int(os.environ.get("CERT_BOT_MIN_DAYS", str(DEFAULT_MIN_DAYS)))
    except ValueError:
        print("::error title=Cert Bot::CERT_BOT_MIN_DAYS must be an integer")
        return 2
    strict = os.environ.get("CERT_BOT_STRICT", "1") == "1"
    return run(hosts, min_days, strict)


if __name__ == "__main__":
    raise SystemExit(main())
