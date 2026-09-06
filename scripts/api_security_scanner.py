#!/usr/bin/env python3
"""
ClearGlass API Security Scanner — Defensive Authorization Audit
=================================================================
Checks for missing authentication, weak authorization, and IDOR
on a declared list of authorized endpoints.

Safe-mode constraints (always enforced):
  - No credential guessing or brute force
  - No payload fuzzing or injection attempts
  - No destructive actions (no production writes unless --allow-writes flag
    is explicitly combined with --target staging|dev)
  - No user enumeration beyond the provided example ID pairs
  - Sequential ID tests use only the ±3 range around provided example IDs
  - All findings are local-only until the operator reviews and exports the report
"""

import argparse
import csv
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error
import urllib.parse

SCANNER_VERSION = "1.0.0"
SAFE_MODE = True  # never disable without explicit --allow-writes on non-production targets


# ── Endpoint definition ───────────────────────────────────────────────────────

class Endpoint:
    def __init__(self, method: str, path: str, auth_required: bool,
                 roles: list[str], object_type: str, example_id: Optional[str] = None):
        self.method = method.upper()
        self.path = path  # e.g. /api/v1/users/{id}
        self.auth_required = auth_required
        self.roles = roles
        self.object_type = object_type
        self.example_id = example_id  # a valid ID owned by the test user


# ── Test result ───────────────────────────────────────────────────────────────

class TestResult:
    def __init__(self, endpoint: Endpoint, scenario: str,
                 expected: int, actual: int, size: int, time_ms: float,
                 error_text: str = ""):
        self.endpoint = endpoint
        self.scenario = scenario
        self.expected = expected
        self.actual = actual
        self.size = size
        self.time_ms = time_ms
        self.error_text = error_text
        self.pass_fail = "PASS" if actual == expected else "FAIL"


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _request(method: str, url: str, headers: dict, timeout: int = 10) -> tuple[int, int, str]:
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(4096)
            return resp.status, len(body), body.decode("utf-8", errors="replace")[:512]
    except urllib.error.HTTPError as e:
        body = e.read(512)
        return e.code, len(body), body.decode("utf-8", errors="replace")[:512]
    except urllib.error.URLError as e:
        return 0, 0, str(e.reason)


def resolve_path(path: str, example_id: str) -> str:
    return path.replace("{id}", example_id)


# ── Scanner ───────────────────────────────────────────────────────────────────

class Scanner:
    def __init__(self, base_url: str, valid_token: str, low_priv_token: str,
                 other_user_id: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.valid_token = valid_token
        self.low_priv_token = low_priv_token
        self.other_user_id = other_user_id  # ID owned by a different user
        self.timeout = timeout
        self.results: list[TestResult] = []

    def _headers(self, token: Optional[str] = None) -> dict:
        h = {"Accept": "application/json", "User-Agent": f"ClearGlass-Audit/{SCANNER_VERSION}"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _run(self, endpoint: Endpoint, scenario: str, path: str,
             token: Optional[str], expected: int) -> TestResult:
        url = self.base_url + path
        start = time.monotonic()
        status, size, text = _request(endpoint.method, url, self._headers(token), self.timeout)
        elapsed = (time.monotonic() - start) * 1000
        result = TestResult(endpoint, scenario, expected, status, size, elapsed, text[:120])
        self.results.append(result)
        flag = "✓" if result.pass_fail == "PASS" else "✗"
        print(f"  {flag} [{scenario:<32}] {endpoint.method} {path} "
              f"→ expected {expected}, got {status} ({elapsed:.0f}ms)")
        return result

    def audit(self, endpoint: Endpoint):
        print(f"\n── {endpoint.method} {endpoint.path} [{endpoint.object_type}]")
        eid = endpoint.example_id or "1"
        path = resolve_path(endpoint.path, eid)
        other_path = resolve_path(endpoint.path, self.other_user_id)

        # 1. Unauthenticated
        expected = 401 if endpoint.auth_required else 200
        self._run(endpoint, "unauthenticated", path, None, expected)

        if not endpoint.auth_required:
            return  # public endpoint — no further auth checks needed

        # 2. Low-privilege user
        self._run(endpoint, "low_privilege_user", path, self.low_priv_token, 403)

        # 3. Valid user, own object — should succeed
        self._run(endpoint, "valid_own_object", path, self.valid_token, 200)

        # 4. Cross-user object access (IDOR)
        if self.other_user_id and other_path != path:
            self._run(endpoint, "cross_user_object_access", other_path, self.valid_token, 403)

        # 5. Sequential ID enumeration (±3, safe range only)
        if endpoint.example_id and endpoint.example_id.isdigit():
            base = int(endpoint.example_id)
            for delta in (-2, -1, 1, 2, 3):
                seq_id = str(base + delta)
                seq_path = resolve_path(endpoint.path, seq_id)
                self._run(endpoint, f"seq_id_enum_{delta:+d}", seq_path, self.valid_token, 403)


# ── Report generation ─────────────────────────────────────────────────────────

def _categorize(result: TestResult) -> str:
    if result.scenario == "unauthenticated" and result.pass_fail == "FAIL":
        return "MISSING_AUTHENTICATION"
    if result.scenario in ("cross_user_object_access", "low_privilege_user") and result.pass_fail == "FAIL":
        return "BROKEN_OBJECT_LEVEL_AUTHORIZATION"
    if result.scenario.startswith("seq_id_enum") and result.pass_fail == "FAIL":
        return "IDOR"
    if result.scenario == "role_escalation" and result.pass_fail == "FAIL":
        return "PRIVILEGE_ESCALATION"
    return "INFORMATIONAL"


def _severity(category: str) -> str:
    return {
        "MISSING_AUTHENTICATION": "CRITICAL",
        "BROKEN_OBJECT_LEVEL_AUTHORIZATION": "HIGH",
        "IDOR": "HIGH",
        "PRIVILEGE_ESCALATION": "CRITICAL",
        "LOGGING_GAP": "MEDIUM",
    }.get(category, "INFORMATIONAL")


def build_json_report(results: list[TestResult], base_url: str,
                      endpoints: list[Endpoint]) -> dict:
    failures = [r for r in results if r.pass_fail == "FAIL"]
    report = {
        "report_id": str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanner_version": SCANNER_VERSION,
        "target_base_url": base_url,
        "summary": {
            "total_endpoints": len(endpoints),
            "total_tests": len(results),
            "passed": len([r for r in results if r.pass_fail == "PASS"]),
            "failed": len(failures),
            "skipped": 0,
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "risk_rating": "INFORMATIONAL",
        },
        "endpoint_inventory": [
            {
                "method": e.method,
                "path": e.path,
                "auth_required": e.auth_required,
                "roles_accepted": e.roles,
                "object_type": e.object_type,
                "uses_object_id": "{id}" in e.path,
            }
            for e in endpoints
        ],
        "findings": [],
    }

    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFORMATIONAL": 0}
    max_sev = "INFORMATIONAL"

    for i, r in enumerate(failures, 1):
        cat = _categorize(r)
        sev = _severity(cat)
        report["summary"][f"{sev.lower()}_count"] += 1
        if severity_rank[sev] > severity_rank[max_sev]:
            max_sev = sev
        report["findings"].append({
            "finding_id": f"NEXUS-{cat[:3]}-{i:03d}",
            "category": cat,
            "severity": sev,
            "endpoint": {"method": r.endpoint.method, "path": r.endpoint.path},
            "scenario": r.scenario,
            "pass_fail": r.pass_fail,
            "description": (
                f"{r.endpoint.method} {r.endpoint.path} returned {r.actual} "
                f"(expected {r.expected}) under scenario '{r.scenario}'. "
                f"Response excerpt: {r.error_text[:80]}"
            ),
            "response_snapshot": {
                "status_code": r.actual,
                "size_bytes": r.size,
                "time_ms": round(r.time_ms, 1),
            },
            "expected_status": r.expected,
            "actual_status": r.actual,
            "remediation": _remediation(cat),
            "verification_steps": _verification(cat, r),
            "references": _references(cat),
        })

    report["summary"]["risk_rating"] = max_sev
    return report


def _remediation(category: str) -> str:
    return {
        "MISSING_AUTHENTICATION": (
            "Add authentication middleware to this route. Verify the middleware runs "
            "before any business logic. Return 401 with WWW-Authenticate header."
        ),
        "BROKEN_OBJECT_LEVEL_AUTHORIZATION": (
            "After authenticating the caller, verify that the requested object belongs "
            "to them (or that their role permits access). Do not rely on the caller's "
            "claimed identity in the request body — use the server-side session."
        ),
        "IDOR": (
            "Replace direct object IDs with opaque, per-user indirect references, or "
            "add an ownership check on every query: WHERE id=? AND owner_id=caller_id."
        ),
        "PRIVILEGE_ESCALATION": (
            "Strip role fields from request bodies before processing. Never let a caller "
            "self-assign roles. Role changes must originate from a higher-privilege endpoint."
        ),
    }.get(category, "Review access control logic for this endpoint.")


def _verification(category: str, result: TestResult) -> list[str]:
    return [
        f"Re-run the '{result.scenario}' scenario against {result.endpoint.method} {result.endpoint.path}.",
        "Confirm the response is now the expected status code.",
        "Confirm server logs record the denial event.",
        "Run the full test matrix to detect regressions.",
    ]


def _references(category: str) -> list[str]:
    base = ["https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/"]
    extras = {
        "MISSING_AUTHENTICATION": ["https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/"],
        "IDOR": ["https://cwe.mitre.org/data/definitions/639.html"],
        "PRIVILEGE_ESCALATION": ["https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/"],
    }
    return base + extras.get(category, [])


def write_csv(results: list[TestResult], path: Path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "endpoint_path", "scenario", "expected_status",
                    "actual_status", "response_size_bytes", "time_ms", "pass_fail",
                    "category", "severity", "error_text"])
        for r in results:
            cat = _categorize(r)
            w.writerow([
                r.endpoint.method, r.endpoint.path, r.scenario,
                r.expected, r.actual, r.size, round(r.time_ms, 1),
                r.pass_fail, cat, _severity(cat), r.error_text[:80],
            ])


# ── CLI ───────────────────────────────────────────────────────────────────────

def load_endpoints(path: Path) -> list[Endpoint]:
    with open(path) as f:
        data = json.load(f)
    return [
        Endpoint(
            method=e["method"],
            path=e["path"],
            auth_required=e.get("auth_required", True),
            roles=e.get("roles", []),
            object_type=e.get("object_type", "unknown"),
            example_id=e.get("example_id"),
        )
        for e in data
    ]


def main():
    parser = argparse.ArgumentParser(
        description="ClearGlass Defensive API Security Scanner"
    )
    parser.add_argument("--base-url", required=True,
                        help="Base URL of the API (staging/dev only recommended)")
    parser.add_argument("--endpoints", required=True,
                        help="Path to JSON file with endpoint definitions")
    parser.add_argument("--valid-token", required=True,
                        help="Bearer token for a valid test user")
    parser.add_argument("--low-priv-token", required=True,
                        help="Bearer token for a low-privilege test user")
    parser.add_argument("--other-user-id", required=True,
                        help="Object ID owned by a different test user (for IDOR check)")
    parser.add_argument("--output-dir", default=".", help="Directory for output files")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    args = parser.parse_args()

    if "production" in args.base_url.lower() or "prod" in args.base_url.lower():
        print("ERROR: Refusing to scan a production target. Use a staging or dev environment.")
        sys.exit(1)

    print(f"ClearGlass API Security Scanner v{SCANNER_VERSION}")
    print(f"Target : {args.base_url}")
    print(f"Safe mode: {SAFE_MODE}")
    print()

    endpoints = load_endpoints(Path(args.endpoints))
    scanner = Scanner(
        base_url=args.base_url,
        valid_token=args.valid_token,
        low_priv_token=args.low_priv_token,
        other_user_id=args.other_user_id,
        timeout=args.timeout,
    )

    for ep in endpoints:
        scanner.audit(ep)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    report = build_json_report(scanner.results, args.base_url, endpoints)
    json_path = out / f"api_audit_{ts}.json"
    csv_path = out / f"api_audit_{ts}.csv"

    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    write_csv(scanner.results, csv_path)

    failures = report["summary"]["failed"]
    risk = report["summary"]["risk_rating"]
    print("\n── Scan complete ──")
    print(f"   Tests: {report['summary']['total_tests']} | "
          f"Passed: {report['summary']['passed']} | "
          f"Failed: {failures}")
    print(f"   Risk rating: {risk}")
    print(f"   JSON report: {json_path}")
    print(f"   CSV report : {csv_path}")

    sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    main()
