#!/usr/bin/env python3
"""End-to-end contract checks against a deployed control plane (staging).

Smoke tests prove the service answers; these prove it still keeps its promises,
read-only, through the public surface a customer and the storefront use:

* the revenue pipeline reports a healthy database;
* the public offer and the side-store catalogue are served with real prices;
* the admin ledger refuses an anonymous caller (the governance gate is live);
* checkout refuses a SKU the server-side price book does not know (prices are
  resolved server-side, never taken from the request).

Nothing here writes: the one POST is rejected before any row is created.
``deploy-promotion.yml`` runs it between staging and the production approval.
Stdlib only.

    python3 scripts/ci/e2e_staging.py --api https://... [--storefront https://...]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

TIMEOUT = 20


def request(method: str, url: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 - https URL from config
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0, str(exc)
    try:
        return status, json.loads(raw or b"null")
    except ValueError:
        return status, raw.decode("utf-8", "replace")


Check = tuple[str, str, str, dict[str, Any] | None, Callable[[int, Any], str | None]]


def expect(status: int, *wanted: int) -> str | None:
    return None if status in wanted else f"status {status}, expected {'/'.join(map(str, wanted))}"


def checks() -> list[Check]:
    def root(status: int, body: Any) -> str | None:
        return expect(status, 200) or (None if isinstance(body, dict) and body.get("service") == "clearglass-commerce" else "unexpected service identity")

    def health(status: int, body: Any) -> str | None:
        if err := expect(status, 200):
            return err
        if not isinstance(body, dict) or body.get("status") != "ok" or body.get("database") != "ok":
            return f"unhealthy: status={body.get('status') if isinstance(body, dict) else body!r}"
        return None

    def offer(status: int, body: Any) -> str | None:
        if err := expect(status, 200):
            return err
        ok = isinstance(body, dict) and all(isinstance(body.get(k), str) and body[k] for k in ("sku", "name"))
        return None if ok else "offer is missing sku/name"

    def catalog(status: int, body: Any) -> str | None:
        if err := expect(status, 200):
            return err
        if not isinstance(body, list) or not body:
            return "catalogue is empty"
        bad = [item for item in body if not isinstance(item.get("sku"), str) or not isinstance(item.get("amount"), int) or item["amount"] <= 0]
        return f"{len(bad)} item(s) without a sku or a positive integer price" if bad else None

    def admin_gate(status: int, _body: Any) -> str | None:
        return expect(status, 401, 403)

    def price_authority(status: int, body: Any) -> str | None:
        if err := expect(status, 400, 422):
            return err
        detail = json.dumps(body).lower()
        return None if "sku" in detail else "rejected, but not for the unknown SKU"

    return [
        ("service identity", "GET", "/", None, root),
        ("revenue pipeline and database healthy", "GET", "/revenue/health", None, health),
        ("public offer served", "GET", "/revenue/public-offer", None, offer),
        ("side-store catalogue priced", "GET", "/sidestore/catalog", None, catalog),
        ("audit ledger refuses anonymous callers", "GET", "/events", None, admin_gate),
        (
            "checkout refuses an unknown SKU",
            "POST",
            "/checkout/session",
            {"items": [{"sku": "cg-e2e-unknown-sku", "quantity": 1}]},
            price_authority,
        ),
    ]


def run(api: str, storefront: str = "") -> list[tuple[str, str | None]]:
    results = []
    for name, method, path, body, verdict in checks():
        status, payload = request(method, api.rstrip("/") + path, body)
        results.append((f"{method} {path} — {name}", verdict(status, payload)))
    if storefront:
        status, _ = request("GET", storefront.rstrip("/") + "/")
        results.append(("GET / — storefront renders", expect(status, 200)))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", required=True)
    parser.add_argument("--storefront", default="")
    args = parser.parse_args(argv)
    if not args.api.startswith("https://") and not args.api.startswith(("http://127.0.0.1", "http://localhost")):
        print("::error::--api must be https:// outside localhost")
        return 2

    results = run(args.api, args.storefront)
    lines = ["### Staging end-to-end", "", "| Result | Check | Detail |", "|---|---|---|"]
    for name, failure in results:
        lines.append(f"| {'FAIL' if failure else 'PASS'} | {name} | {failure or ''} |")
        print(f"{'FAIL' if failure else 'PASS'}  {name}{'  — ' + failure if failure else ''}")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    failed = [name for name, failure in results if failure]
    if failed:
        print(f"::error title=Staging E2E::{len(failed)} check(s) failed; production promotion is blocked")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
