#!/usr/bin/env python3
"""Low-volume edge smoke tests using Python's standard library only."""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Iterable

EXPECTED_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": None,
    "strict-transport-security": None,
    "content-security-policy-report-only": None,
}


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        candidate = values.get("src") if tag in {"script", "img", "source"} else values.get("href")
        if candidate:
            self.urls.append(candidate)


def request(url: str, method: str = "GET", headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes, str]:
    req = urllib.request.Request(url, method=method, headers=headers or {"User-Agent": "ClearGlass-Edge-Smoke/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read(1024 * 1024), response.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read(64 * 1024), exc.geturl()


def same_origin_assets(base_url: str, html: bytes, limit: int = 5) -> Iterable[str]:
    parser = AssetParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    base = urllib.parse.urlparse(base_url)
    emitted = 0
    seen: set[str] = set()
    for candidate in parser.urls:
        absolute = urllib.parse.urljoin(base_url, candidate)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != base.netloc:
            continue
        clean = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))
        if clean in seen:
            continue
        seen.add(clean)
        yield clean
        emitted += 1
        if emitted >= limit:
            break


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--require-edge", action="store_true", help="Fail if expected edge headers are absent.")
    parser.add_argument("--api-url", default="", help="Optional non-destructive API health/read endpoint.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    failures: list[str] = []
    warnings: list[str] = []

    status, headers, body, final_url = request(base_url)
    print(f"homepage: {status} -> {final_url}")
    if not 200 <= status < 400:
        failures.append(f"homepage returned {status}")
    if not final_url.startswith("https://"):
        failures.append("final homepage URL is not HTTPS")

    for name, expected in EXPECTED_HEADERS.items():
        value = headers.get(name)
        if value is None:
            message = f"missing expected edge header: {name}"
            (failures if args.require_edge else warnings).append(message)
        elif expected is not None and value.lower() != expected.lower():
            failures.append(f"unexpected {name}: {value!r}")

    # Legacy frame header is intentionally checked while the rollout retains it.
    if headers.get("x-frame-options", "").upper() != "SAMEORIGIN":
        warnings.append("X-Frame-Options is absent or not SAMEORIGIN")

    # Exercise a handful of real same-origin assets discovered from the page.
    for asset in same_origin_assets(base_url, body):
        asset_status, asset_headers, _, _ = request(asset, method="HEAD")
        print(f"asset: {asset_status} {asset} [{asset_headers.get('content-type', 'unknown')}] ")
        if not 200 <= asset_status < 400:
            failures.append(f"asset failed: {asset} -> {asset_status}")

    # Two ordinary requests provide visibility into CDN cache behavior without assuming a hit.
    _, first_headers, _, _ = request(base_url)
    _, second_headers, _, _ = request(base_url)
    print(f"cache: first={first_headers.get('cf-cache-status', 'n/a')} second={second_headers.get('cf-cache-status', 'n/a')}")

    if args.api_url:
        api_status, api_headers, _, api_final = request(args.api_url)
        print(f"api: {api_status} -> {api_final}; acao={api_headers.get('access-control-allow-origin', 'n/a')}")
        if not 200 <= api_status < 500:
            failures.append(f"API probe failed unexpectedly: {api_status}")

    for warning in warnings:
        print(f"WARN: {warning}")
    for failure in failures:
        print(f"ERROR: {failure}", file=sys.stderr)

    if failures:
        return 1
    print("Smoke tests completed successfully." if args.require_edge else "Smoke tests completed; edge-header absence is warning-only without --require-edge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
