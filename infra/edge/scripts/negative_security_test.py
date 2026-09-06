#!/usr/bin/env python3
"""Safe, low-volume negative edge tests. Dry-run unless --execute is supplied.

This is not a load test, vulnerability scanner, brute-force tool or DDoS simulator.
It sends at most a handful of requests designed to validate policy behavior.
"""

from __future__ import annotations

import argparse
import urllib.error
import urllib.parse
import urllib.request


PROBES = [
    ("suspicious-user-agent", "/", {"User-Agent": "sqlmap-safe-edge-validation"}),
    ("sqli-query", "/?edge_test=" + urllib.parse.quote("1' OR '1'='1"), {"User-Agent": "ClearGlass-Edge-Test/1.0"}),
    ("xss-query", "/?edge_test=" + urllib.parse.quote("<script>alert(1)</script>"), {"User-Agent": "ClearGlass-Edge-Test/1.0"}),
    ("path-traversal", "/%2e%2e/%2e%2e/.env", {"User-Agent": "ClearGlass-Edge-Test/1.0"}),
    ("scanner-path", "/.git/config", {"User-Agent": "ClearGlass-Edge-Test/1.0"}),
    ("oversized-header-modest", "/", {"User-Agent": "ClearGlass-Edge-Test/1.0", "X-Edge-Test-Padding": "A" * 4096}),
    ("cache-poisoning-header", "/?edge_cache_probe=1", {"User-Agent": "ClearGlass-Edge-Test/1.0", "X-Forwarded-Host": "invalid.example"}),
]


def send(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str]]:
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}


def classify(status: int, headers: dict[str, str]) -> str:
    if status == 429:
        return "rate-limited"
    if status in {401, 403}:
        if "cf-mitigated" in headers or "cf-ray" in headers:
            return "blocked-or-challenged-at-edge"
        return "denied"
    if 200 <= status < 400:
        return "allowed"
    return f"status-{status}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="Send the safe low-volume probes.")
    mode.add_argument("--dry-run", action="store_true", help="Print probes only (default).")
    parser.add_argument("--origin-url", default="", help="Optional known origin URL to check for direct reachability.")
    parser.add_argument("--rate-probe-count", type=int, default=3, help="Ordinary repeated GETs; capped at 20.")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    execute = args.execute
    rate_count = min(max(args.rate_probe_count, 1), 20)

    print("Mode:", "EXECUTE (safe low volume)" if execute else "DRY RUN")
    print("This tool never performs credential stuffing, destructive payloads, port scans or DDoS simulation.")

    for name, path, headers in PROBES:
        url = base + path
        if not execute:
            print(f"PLAN {name}: GET {url}; headers={list(headers)}")
            continue
        status, response_headers = send(url, headers)
        print(f"RESULT {name}: {status} {classify(status, response_headers)} ray={response_headers.get('cf-ray', 'n/a')}")

    if not execute:
        print(f"PLAN rate-behavior: {rate_count} ordinary GET requests to {base}/ (well below DDoS/load-test levels)")
    else:
        results = []
        for _ in range(rate_count):
            status, response_headers = send(base + "/", {"User-Agent": "ClearGlass-Edge-Rate-Probe/1.0"})
            results.append(classify(status, response_headers))
        print("RESULT rate-behavior:", ", ".join(results))

    if args.origin_url:
        if not execute:
            print(f"PLAN origin-exposure: single GET {args.origin_url}")
        else:
            status, _ = send(args.origin_url, {"User-Agent": "ClearGlass-Origin-Exposure-Check/1.0"})
            print(f"RESULT origin-exposure: {status}; direct reachability is a known GitHub Pages limitation if successful")

    print("NOT SIMULATED: country/ASN source location, verified crawler identity, trusted-IP exception, signed webhook identity, credential stuffing, or provider-scale DDoS. Validate those with provider analytics/staging sources, not spoofed headers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
