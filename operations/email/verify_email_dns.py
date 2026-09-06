#!/usr/bin/env python3
"""Verify the public DNS controls required for ClearGlassInc business email.

Uses Google's DNS-over-HTTPS JSON API so the check remains dependency-free and
works even when the local resolver is unavailable. This tool is read-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DNS_API = "https://dns.google/resolve"
DOMAIN = "clearglassinc.com"
EXPECTED_MX = "smtp.google.com."
SPF_TOKEN = "include:_spf.google.com"


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def query_dns(name: str, record_type: str, timeout: float = 5.0) -> list[str]:
    url = f"{DNS_API}?{urlencode({'name': name, 'type': record_type})}"
    request = Request(url, headers={"Accept": "application/dns-json", "User-Agent": "ClearGlassInc-DNS-Check/1.0"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS endpoint
        payload = json.load(response)
    if payload.get("Status") != 0:
        return []
    return [str(answer["data"]) for answer in payload.get("Answer", []) if "data" in answer]


def unquote_txt(value: str) -> str:
    """Join the quoted chunks returned for a DNS TXT record."""
    return value.replace('" "', "").strip('"')


def evaluate(
    lookup: Callable[[str, str], list[str]],
    *,
    domain: str = DOMAIN,
    dkim_selector: str | None = None,
) -> list[Check]:
    mx = lookup(domain, "MX")
    mx_hosts = {entry.split(maxsplit=1)[-1].lower() for entry in mx}
    checks = [
        Check("MX", EXPECTED_MX in mx_hosts, f"published: {', '.join(mx) or 'none'}"),
    ]

    root_txt = [unquote_txt(value) for value in lookup(domain, "TXT")]
    spf = [value for value in root_txt if value.lower().startswith("v=spf1")]
    checks.append(
        Check(
            "SPF",
            len(spf) == 1 and SPF_TOKEN in spf[0].lower(),
            "one Google-authorized SPF record found" if len(spf) == 1 and SPF_TOKEN in spf[0].lower() else f"published SPF records: {spf or 'none'}",
        )
    )

    dmarc = [unquote_txt(value) for value in lookup(f"_dmarc.{domain}", "TXT")]
    valid_dmarc = len(dmarc) == 1 and dmarc[0].lower().startswith("v=dmarc1;")
    checks.append(Check("DMARC", valid_dmarc, f"published: {dmarc[0] if len(dmarc) == 1 else dmarc or 'none'}"))

    if dkim_selector:
        dkim = [unquote_txt(value) for value in lookup(f"{dkim_selector}._domainkey.{domain}", "TXT")]
        valid_dkim = len(dkim) == 1 and "v=dkim1" in dkim[0].lower() and "p=" in dkim[0].lower()
        checks.append(Check("DKIM", valid_dkim, "public key published" if valid_dkim else f"published: {dkim or 'none'}"))
    else:
        checks.append(Check("DKIM", False, "not checked: pass --dkim-selector after Google generates the key"))

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify ClearGlassInc email DNS without changing it.")
    parser.add_argument("--domain", default=DOMAIN)
    parser.add_argument("--dkim-selector", help="Selector generated in Google Admin (often 'google').")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    try:
        checks = evaluate(lambda name, kind: query_dns(name, kind, args.timeout), domain=args.domain, dkim_selector=args.dkim_selector)
    except Exception as exc:
        print(f"ERROR: DNS lookup failed: {exc}", file=sys.stderr)
        return 2

    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
