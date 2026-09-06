# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Percival v9 Policy Governor service — stdlib-only HTTP entry point.

Speaks the same contract as the OPA sidecar in the deployment blueprint, so the
orchestrator's ``POLICY_ENDPOINT`` works unchanged against either backend:

    POST /v1/data/percival/authz/allow
        body:     {"input": {"identity": "...", "capability": "..."}}
        response: {"result": {"allow": bool, "reason": "...", ...}}
    GET  /healthz
        response: {"ok": true, "deny_all": bool, "ledger_entries": int}

Fail-closed at the transport layer too: malformed requests, unknown routes,
and internal errors all yield ``allow: false`` — never an implicit grant.

Run: ``python -m percival_v9.cmd.governor --port 8181 [--self-check]``
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from percival_v9.internal.audit import AuditLedger
from percival_v9.internal.policy.engine import Capability, PolicyGovernor, Risk

AUTHZ_PATH = "/v1/data/percival/authz/allow"
DEFAULT_POLICIES = Path(__file__).resolve().parents[1] / "policies" / "capabilities.json"


def load_governor(policies_path: Path = DEFAULT_POLICIES) -> PolicyGovernor:
    """Build a PolicyGovernor from the versioned capability schema."""
    schema = json.loads(policies_path.read_text())
    if schema.get("version") != 1:
        raise ValueError(f"unsupported capability schema version: {schema.get('version')!r}")
    governor = PolicyGovernor(ledger=AuditLedger())
    for identity, spec in schema.get("identities", {}).items():
        for cap in spec.get("capabilities", []):
            governor.grant(identity, Capability(cap["name"], Risk(cap["risk"])))
    return governor


class GovernorHandler(BaseHTTPRequestHandler):
    """HTTP surface over the PolicyGovernor. One governor per server."""

    governor: PolicyGovernor  # attached by make_server()

    def log_message(self, fmt: str, *args: Any) -> None:  # quiet by default
        return

    def _send(self, status: int, body: dict[str, Any]) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _deny(self, status: int, reason: str) -> None:
        self._send(status, {"result": {"allow": False, "reason": reason}})

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path != "/healthz":
            self._deny(404, "unknown route (fail-closed)")
            return
        self._send(
            200,
            {
                "ok": True,
                "deny_all": self.governor.deny_all,
                "ledger_entries": len(self.governor.ledger),
            },
        )

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        if self.path != AUTHZ_PATH:
            self._deny(404, "unknown route (fail-closed)")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            request = payload["input"]
            identity, capability = str(request["identity"]), str(request["capability"])
        except (KeyError, TypeError, ValueError):
            self._deny(400, "malformed request (fail-closed)")
            return
        decision = self.governor.evaluate(identity, capability)
        self._send(
            200,
            {
                "result": {
                    "allow": decision.allow,
                    "reason": decision.reason,
                    "identity": decision.identity,
                    "capability": decision.capability,
                }
            },
        )


def make_server(port: int, policies_path: Path = DEFAULT_POLICIES) -> ThreadingHTTPServer:
    """Create (but do not start) a governor server bound to ``port``."""
    handler = type("BoundGovernorHandler", (GovernorHandler,), {})
    handler.governor = load_governor(policies_path)
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def self_check(policies_path: Path = DEFAULT_POLICIES) -> dict[str, Any]:
    """Offline governance self-check, mirroring daily_loop-style gates."""
    governor = load_governor(policies_path)
    checks = {
        "deny_by_default": not governor.evaluate("nobody", "anything").allow,
        "low_risk_allowed": governor.evaluate("orchestrator-worker", "read_metrics").allow,
        "gated_risk_blocked": not governor.evaluate("orchestrator-worker", "update_pricing").allow,
        "ledger_intact": governor.ledger.verify(),
    }
    return {"ok": all(checks.values()), "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Percival v9 Policy Governor service")
    parser.add_argument("--port", type=int, default=8181)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--self-check", action="store_true", help="run checks and exit")
    args = parser.parse_args(argv)

    if args.self_check:
        report = self_check(args.policies)
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1

    server = make_server(args.port, args.policies)
    print(f"percival-governor listening on 127.0.0.1:{args.port} (POST {AUTHZ_PATH})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
