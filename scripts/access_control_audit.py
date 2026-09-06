# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#!/usr/bin/env python3
"""Defensive access-control (IDOR / missing-auth) audit harness.

This is a DEFENSIVE, AUDIT-ORIENTED tool for *authorized* internal testing only.
It verifies that protected endpoints enforce authentication and object-level
authorization, aligned with the NSA/CISA/ACSC "Preventing Web Application
Access Control Abuse" advisory and the OWASP WSTG IDOR testing guidance.

What it does
------------
For each configured endpoint it runs up to four read-only checks:
  1. no-auth        - request with no credentials; expects 401/403.
  2. owner          - request as the legitimate owner; records the baseline.
  3. cross-account  - request the owner's object as a *different* user; a 2xx
                      (especially one matching the owner body) is a likely IDOR.
  4. id-swap        - request as the owner but with the object identifier moved
                      by one; a 2xx for an object the owner does not own is a
                      likely IDOR.

What it deliberately does NOT do
--------------------------------
  * It does not brute-force or enumerate identifiers (a single +1 swap only).
  * It defaults to safe HTTP methods (GET/HEAD/OPTIONS). Write methods require
    an explicit opt-in and only ever send the body you put in the config.
  * It will not run until you confirm authorization in the config file.
  * It refuses placeholder hosts (example.com, localhost, ...) unless opted in,
    so the shipped template is inert by design.
  * It throttles requests and enforces a hard request cap.

Usage
-----
  cp scripts/access_control_audit.example.json my-scope.json
  # edit my-scope.json: set authorization.confirmed=true, real endpoints/creds
  python scripts/access_control_audit.py --config my-scope.json --report out.json

Run ``python scripts/access_control_audit.py --print-template`` to emit a fresh
config skeleton.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Hosts that must never be hit by accident. The shipped template uses these so a
# fresh checkout is inert until pointed at a real, authorized target.
PLACEHOLDER_HOSTS = {
    "example.com",
    "example.org",
    "example.net",
    "localhost",
    "127.0.0.1",
    "::1",
    "test.invalid",
}

CONFIG_TEMPLATE: dict[str, Any] = {
    "authorization": {
        "confirmed": False,
        "scope": "Describe exactly which systems and time window you are authorized to test.",
        "authorized_by": "Name / ticket reference for the engagement authorization.",
    },
    "settings": {
        "timeout_seconds": 10,
        "delay_seconds": 1.0,
        "max_requests": 200,
        "allow_write_methods": False,
        "allow_placeholder_hosts": False,
        "compare_bodies": True,
    },
    "accounts": {
        "user_a": {
            "headers": {"Authorization": "Bearer <token-for-user-a>"},
            "cookies": {"session": "<session-for-user-a>"},
        },
        "user_b": {
            "headers": {"Authorization": "Bearer <token-for-user-b>"},
            "cookies": {"session": "<session-for-user-b>"},
        },
    },
    "endpoints": [
        {
            "name": "Get order (path id)",
            "method": "GET",
            "url": "https://example.com/api/v1/orders/456",
            "owner": "user_a",
            "cross_account": "user_b",
            "body": None,
            "expect_owner_status": [200],
            "expect_denied_status": [401, 403, 404],
        }
    ],
}


@dataclass
class Finding:
    endpoint: str
    check: str
    severity: str  # INFO | WARN | FINDING | ERROR
    status: int | None
    detail: str
    request_url: str = ""


@dataclass
class Response:
    status: int
    body: bytes
    error: str | None = None


@dataclass
class Budget:
    """Hard cap + throttle shared across all checks to prevent enumeration/DoS."""

    max_requests: int
    delay_seconds: float
    used: int = field(default=0)

    def spend(self) -> bool:
        if self.used >= self.max_requests:
            return False
        if self.used:
            time.sleep(self.delay_seconds)
        self.used += 1
        return True


def swap_numeric_id(url: str) -> tuple[str, bool]:
    """Move the first numeric path segment (then query value) by +1. No brute force."""
    parsed = urlparse(url)
    parts = parsed.path.rstrip("/").split("/")
    changed = False
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].isdigit():
            parts[i] = str(int(parts[i]) + 1)
            changed = True
            break
    new_path = "/".join(parts)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if not changed:
        for key, vals in qs.items():
            if vals and vals[0].isdigit():
                qs[key] = [str(int(vals[0]) + 1)]
                changed = True
                break
    if not changed:
        return url, False
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(path=new_path, query=new_query)), True


def is_placeholder_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in PLACEHOLDER_HOSTS


def build_headers(account: dict[str, Any] | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if not account:
        return headers
    headers.update({str(k): str(v) for k, v in (account.get("headers") or {}).items()})
    cookies = account.get("cookies") or {}
    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    return headers


def send(url: str, method: str, headers: dict[str, str], body: Any, timeout: float) -> Response:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (scheme validated below)
            return Response(status=resp.status, body=resp.read())
    except urllib.error.HTTPError as exc:
        return Response(status=exc.code, body=exc.read() or b"")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return Response(status=0, body=b"", error=str(exc))


def looks_authorized(status: int) -> bool:
    return 200 <= status < 300


def validate_config(cfg: dict[str, Any], allow_placeholder: bool) -> list[str]:
    """Return a list of blocking errors. Empty list means safe to run."""
    errors: list[str] = []
    auth = cfg.get("authorization") or {}
    if not auth.get("confirmed"):
        errors.append(
            "authorization.confirmed is not true. Set it to true only after you have "
            "documented authorization to test the configured targets."
        )
    if not str(auth.get("scope", "")).strip():
        errors.append("authorization.scope is empty; describe what you are authorized to test.")

    endpoints = cfg.get("endpoints") or []
    if not endpoints:
        errors.append("No endpoints configured.")

    settings = cfg.get("settings") or {}
    allow_write = bool(settings.get("allow_write_methods"))
    allow_ph = allow_placeholder or bool(settings.get("allow_placeholder_hosts"))

    for ep in endpoints:
        name = ep.get("name", ep.get("url", "<unnamed>"))
        url = ep.get("url", "")
        scheme = urlparse(url).scheme.lower()
        if scheme not in {"http", "https"}:
            errors.append(f"{name}: url must be http(s).")
        if is_placeholder_host(url) and not allow_ph:
            errors.append(
                f"{name}: '{urlparse(url).hostname}' is a placeholder host. This is the inert "
                "template default; point it at an authorized target (or set "
                "settings.allow_placeholder_hosts for local lab use)."
            )
        method = str(ep.get("method", "GET")).upper()
        if method not in SAFE_METHODS and not allow_write:
            errors.append(
                f"{name}: method {method} is a write method. Set settings.allow_write_methods "
                "to true to permit it (only the configured body is ever sent)."
            )
    return errors


def audit_endpoint(ep: dict[str, Any], cfg: dict[str, Any], budget: Budget) -> list[Finding]:
    settings = cfg.get("settings") or {}
    accounts = cfg.get("accounts") or {}
    timeout = float(settings.get("timeout_seconds", 10))
    compare_bodies = bool(settings.get("compare_bodies", True))

    name = ep.get("name", ep.get("url", "<unnamed>"))
    url = ep["url"]
    method = str(ep.get("method", "GET")).upper()
    body = ep.get("body")
    denied = set(ep.get("expect_denied_status", [401, 403, 404]))

    owner = accounts.get(ep.get("owner", ""))
    cross_name = ep.get("cross_account", "")
    cross = accounts.get(cross_name)

    findings: list[Finding] = []
    owner_body: bytes | None = None

    def run(check: str, target_url: str, account: dict[str, Any] | None) -> Response | None:
        if not budget.spend():
            findings.append(
                Finding(name, check, "ERROR", None, "Request budget exhausted; skipped.", target_url)
            )
            return None
        return send(target_url, method, build_headers(account), body, timeout)

    # 1. no-auth ------------------------------------------------------------
    resp = run("no-auth", url, None)
    if resp is not None:
        if resp.error:
            findings.append(Finding(name, "no-auth", "ERROR", 0, resp.error, url))
        elif looks_authorized(resp.status):
            findings.append(
                Finding(name, "no-auth", "FINDING", resp.status,
                        "Endpoint returned success with no credentials (missing authentication).", url)
            )
        elif resp.status in denied:
            findings.append(Finding(name, "no-auth", "INFO", resp.status,
                                    "Correctly rejected unauthenticated request.", url))
        else:
            findings.append(Finding(name, "no-auth", "WARN", resp.status,
                                    "Unexpected status for unauthenticated request.", url))

    # 2. owner baseline -----------------------------------------------------
    if owner is not None:
        resp = run("owner", url, owner)
        if resp is not None and not resp.error:
            owner_body = resp.body
            findings.append(Finding(name, "owner", "INFO", resp.status,
                                    "Owner baseline response recorded.", url))
        elif resp is not None:
            findings.append(Finding(name, "owner", "ERROR", 0, resp.error or "", url))

    # 3. cross-account ------------------------------------------------------
    if cross is not None:
        resp = run("cross-account", url, cross)
        if resp is not None and not resp.error:
            if looks_authorized(resp.status):
                same = compare_bodies and owner_body is not None and resp.body == owner_body
                detail = (
                    f"User '{cross_name}' received a success response for an object owned by "
                    f"'{ep.get('owner')}'"
                    + (" and the body matches the owner response (strong IDOR signal)." if same
                       else " (possible IDOR; verify ownership manually).")
                )
                findings.append(Finding(name, "cross-account", "FINDING", resp.status, detail, url))
            elif resp.status in denied:
                findings.append(Finding(name, "cross-account", "INFO", resp.status,
                                        "Cross-account access correctly denied.", url))
            else:
                findings.append(Finding(name, "cross-account", "WARN", resp.status,
                                        "Unexpected status for cross-account request.", url))

    # 4. id-swap as owner ---------------------------------------------------
    swapped_url, changed = swap_numeric_id(url)
    if changed and owner is not None:
        resp = run("id-swap", swapped_url, owner)
        if resp is not None and not resp.error:
            if looks_authorized(resp.status):
                findings.append(
                    Finding(name, "id-swap", "WARN", resp.status,
                            "Adjacent object id returned success for the owner. Confirm the owner "
                            "is authorized for this object; if not, this is an IDOR.", swapped_url)
                )
            elif resp.status in denied:
                findings.append(Finding(name, "id-swap", "INFO", resp.status,
                                        "Adjacent object id correctly denied.", swapped_url))
            else:
                findings.append(Finding(name, "id-swap", "WARN", resp.status,
                                        "Unexpected status for id-swap request.", swapped_url))

    return findings


def summarize(findings: list[Finding]) -> int:
    by_sev: dict[str, int] = {}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1

    print("== Access-Control Audit ==")
    print(
        "FINDING: {f} | WARN: {w} | ERROR: {e} | INFO: {i}".format(
            f=by_sev.get("FINDING", 0), w=by_sev.get("WARN", 0),
            e=by_sev.get("ERROR", 0), i=by_sev.get("INFO", 0),
        )
    )
    print()
    icons = {"FINDING": "🚨", "WARN": "⚠️", "ERROR": "❗", "INFO": "ℹ️"}
    for f in findings:
        line = f"{icons.get(f.severity, '-')} [{f.severity}] {f.endpoint} :: {f.check}"
        if f.status is not None:
            line += f" (HTTP {f.status})"
        print(line)
        print(f"      {f.detail}")
    if not findings:
        print("No checks ran.")
    # Exit non-zero when a likely access-control flaw is present.
    return 1 if by_sev.get("FINDING", 0) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="Path to the JSON scope/config file.")
    parser.add_argument("--report", help="Write the full findings report as JSON to this path.")
    parser.add_argument("--allow-placeholder-hosts", action="store_true",
                        help="Permit example.com/localhost targets (local lab use only).")
    parser.add_argument("--print-template", action="store_true",
                        help="Print a fresh config skeleton to stdout and exit.")
    args = parser.parse_args()

    if args.print_template:
        print(json.dumps(CONFIG_TEMPLATE, indent=2))
        return 0

    if not args.config:
        parser.error("--config is required (or use --print-template).")

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON config: {exc}", file=sys.stderr)
        return 2

    errors = validate_config(cfg, allow_placeholder=args.allow_placeholder_hosts)
    if errors:
        print("Refusing to run. Resolve these first:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    settings = cfg.get("settings") or {}
    budget = Budget(
        max_requests=int(settings.get("max_requests", 200)),
        delay_seconds=float(settings.get("delay_seconds", 1.0)),
    )

    findings: list[Finding] = []
    for ep in cfg.get("endpoints", []):
        findings.extend(audit_endpoint(ep, cfg, budget))

    if args.report:
        Path(args.report).write_text(
            json.dumps([asdict(f) for f in findings], indent=2), encoding="utf-8"
        )
        print(f"Report written to {args.report} ({budget.used} requests sent)\n")

    return summarize(findings)


if __name__ == "__main__":
    raise SystemExit(main())
