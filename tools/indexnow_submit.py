#!/usr/bin/env python3
"""Submit canonical ClearGlass URLs to IndexNow with an owner-provided key."""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request

HOST = "www.clearglassinc.com"
ENDPOINT = "https://api.indexnow.org/indexnow"


def canonical_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != HOST or parsed.username or parsed.password:
        raise ValueError(f"URL must be an HTTPS URL on {HOST}: {value}")
    if parsed.port not in (None, 443) or parsed.fragment:
        raise ValueError(f"URL cannot contain a nonstandard port or fragment: {value}")
    return value


def submit(urls: list[str], key: str) -> int:
    if not (8 <= len(key) <= 128) or not all(char.isalnum() or char == "-" for char in key):
        raise ValueError("INDEXNOW_KEY must be 8-128 ASCII letters, digits, or hyphens")
    payload = json.dumps({
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/{key}.txt",
        "urlList": [canonical_url(url) for url in urls],
    }).encode()
    request = urllib.request.Request(
        ENDPOINT, data=payload, method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", help=f"HTTPS URLs on {HOST}")
    args = parser.parse_args()
    key = os.environ.get("INDEXNOW_KEY", "")
    if not key:
        parser.error("INDEXNOW_KEY is required")
    status = submit(args.urls[:10_000], key)
    if status not in {200, 202}:
        raise RuntimeError(f"IndexNow returned HTTP {status}")
    print(f"IndexNow accepted {len(args.urls[:10_000])} URL(s) with HTTP {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
