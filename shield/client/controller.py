"""Shield G01 client lifecycle controller. Runs inside the client test namespace.

    python3 -m shield.client.controller connect|check|disconnect|apply-config ...

Each command prints one JSON object: the final state, the failure state if any,
and the ordered state path. Every transition is also emitted as a test-only
telemetry event. The controller never reads key material into its own output:
the private key is passed to `wg` by file path only.

What it can and cannot tell apart, by WireGuard's design: an unknown, invalid
or revoked peer gets no reply at all, so all three surface as
HANDSHAKE_FAILURE. GATEWAY_UNAVAILABLE means the gateway host does not answer
on the underlay; a reachable host with no answering tunnel is a handshake
failure.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from shield import common
from shield.client.config import ConfigError, ShieldConfig
from shield.client.telemetry import Telemetry
from shield.probes import dns_query, http_get, underlay_state

STATES = (
    "INITIALIZED",
    "CONFIG_VALIDATING",
    "CONFIG_VALID",
    "AUTHENTICATING",
    "CONNECTING",
    "HANDSHAKING",
    "CONNECTED",
    "HEALTHY",
    "DISCONNECTING",
    "DISCONNECTED",
    "CONFIG_FAILURE",
    "AUTH_FAILURE",
    "GATEWAY_UNAVAILABLE",
    "HANDSHAKE_FAILURE",
    "TUNNEL_FAILURE",
    "DNS_FAILURE",
    "REVOKED",
    "NETWORK_LOCK_ACTIVE",
)
FAILURES = frozenset(s for s in STATES if s.endswith("_FAILURE")) | {"GATEWAY_UNAVAILABLE", "REVOKED"}


class Controller:
    def __init__(self, telemetry: Telemetry, iface: str = common.WG_CLIENT):
        self.telemetry = telemetry
        self.iface = iface
        self.path: list[str] = []
        self.failure: str | None = None
        self.error_class = "none"

    def to(self, state: str, **fields: object) -> None:
        if state not in STATES:
            raise ValueError(f"unknown state {state}")
        self.path.append(state)
        result = "failure" if state in FAILURES else "ok"
        if state in FAILURES:
            self.failure = state
        self.telemetry.emit(
            component="client",
            event_type="state_transition",
            state=state,
            result=result,
            error_class=self.error_class,
            **fields,
        )

    def fail(self, state: str, error_class: str) -> dict[str, object]:
        self.error_class = error_class
        self.to(state)
        common.wg_link_del(self.iface)
        self.to("NETWORK_LOCK_ACTIVE", tunnel_state="down")
        return self.result()

    def result(self) -> dict[str, object]:
        return {
            "final_state": self.path[-1] if self.path else None,
            "failure_state": self.failure,
            "error_class": self.error_class,
            "path": self.path,
        }

    # -- commands -----------------------------------------------------------

    def connect(self, config_path: Path, key_path: Path) -> dict[str, object]:
        self.to("INITIALIZED")
        self.to("CONFIG_VALIDATING")
        try:
            config = ShieldConfig.load(config_path)
        except ConfigError as exc:
            # A DNS-policy violation is a DNS failure: the tunnel must not come up
            # with a resolver outside the test policy.
            state = "DNS_FAILURE" if exc.error_class == "dns_policy_rejected" else "CONFIG_FAILURE"
            return self.fail(state, exc.error_class)
        self.to("CONFIG_VALID", config_version=config.configuration_version)

        self.to("AUTHENTICATING")
        if not _key_file_ok(key_path):
            return self.fail("AUTH_FAILURE", "client_key_invalid")
        self.to("CONNECTING", credential_state="loaded")

        if underlay_state(config.gateway_host, config.gateway_port) != "up":
            return self.fail("GATEWAY_UNAVAILABLE", "underlay_unreachable")
        try:
            self._tunnel_up(config, key_path)
        except Exception:  # noqa: BLE001 - any data-plane error is a tunnel failure
            return self.fail("TUNNEL_FAILURE", "tunnel_setup_failed")

        self.to("HANDSHAKING", tunnel_state="up")
        deadline = time.monotonic() + common.HANDSHAKE_TIMEOUT_S
        while time.monotonic() < deadline and common.latest_handshake(self.iface) == 0:
            time.sleep(0.1)
        if common.latest_handshake(self.iface) == 0:
            return self.fail("HANDSHAKE_FAILURE", "no_handshake")
        self.to("CONNECTED", handshake_state="complete", tunnel_state="up")

        try:
            rcode, answer = dns_query("service.shield.test", common.TUNNEL_GATEWAY, common.DNS_PORT)
        except OSError:
            return self.fail("DNS_FAILURE", "resolver_unreachable")
        if rcode != 0 or answer != common.TUNNEL_GATEWAY:
            return self.fail("DNS_FAILURE", "unexpected_answer")
        if not self._service_ok():
            return self.fail("TUNNEL_FAILURE", "synthetic_route_failed")
        self.to("HEALTHY", dns_policy_state="active", tunnel_state="up", handshake_state="complete")
        return self.result()

    def check(self) -> dict[str, object]:
        if not common.link_exists(self.iface):
            return self.fail("TUNNEL_FAILURE", "interface_missing")
        try:
            status, _ = http_get(common.TUNNEL_GATEWAY, common.HEALTH_PORT, "/health")
        except OSError:
            return self.fail("TUNNEL_FAILURE", "health_unreachable")
        if status != 200:
            return self.fail("TUNNEL_FAILURE", "health_status")
        self.to("HEALTHY", tunnel_state="up")
        return self.result()

    def disconnect(self) -> dict[str, object]:
        self.to("DISCONNECTING")
        common.wg_link_del(self.iface)
        self.to("DISCONNECTED", tunnel_state="down")
        return self.result()

    def apply_config(self, candidate: Path, approved: Path) -> dict[str, object]:
        """Adopt candidate only if it validates; otherwise keep the approved config."""
        self.to("CONFIG_VALIDATING")
        try:
            config = ShieldConfig.load(candidate)
        except ConfigError as exc:
            self.error_class = exc.error_class
            self.to("CONFIG_FAILURE")
            ShieldConfig.load(approved)  # the approved config must still validate
            self.error_class = "rolled_back"
            self.to("CONFIG_VALID", config_version="1")
            return self.result() | {"adopted": False}
        shutil.copyfile(candidate, approved)
        self.to("CONFIG_VALID", config_version=config.configuration_version)
        return self.result() | {"adopted": True}

    # -- data plane ---------------------------------------------------------

    def _tunnel_up(self, config: ShieldConfig, key_path: Path) -> None:
        """Fresh interface every time, pinned to the gateway key in the validated config."""
        common.wg_link_del(self.iface)
        common.wg_link_add(self.iface)
        common.sh([
            "wg", "set", self.iface,
            "private-key", str(key_path),
            "peer", config.public_key,
            "allowed-ips", common.TUNNEL_NET,
            "endpoint", config.gateway_endpoint,
            "persistent-keepalive", "1",
        ])
        common.sh(["ip", "addr", "add", config.tunnel_address, "dev", self.iface])
        common.sh(["ip", "link", "set", self.iface, "up"])

    def _service_ok(self) -> bool:
        try:
            status, body = http_get(common.TUNNEL_GATEWAY, common.HTTP_PORT)
        except OSError:
            return False
        return status == 200 and common.SERVICE_MARKER in body


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _key_file_ok(path: Path) -> bool:
    """The private key file exists, is private to its owner, and has key shape."""
    try:
        if path.stat().st_mode & 0o077:
            return False
    except OSError:
        return False
    value = _read(path)
    return value is not None and common.is_wireguard_key(value)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="shield.client.controller")
    parser.add_argument("command", choices=["connect", "check", "disconnect", "apply-config"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--approved", type=Path)
    parser.add_argument("--key", type=Path)
    parser.add_argument("--telemetry", type=Path)
    for name in ("test-id", "run-id", "environment-id", "commit-sha"):
        parser.add_argument(f"--{name}", default="unset")
    args = parser.parse_args(argv)
    telemetry = Telemetry(
        args.telemetry,
        test_id=args.test_id,
        run_id=args.run_id,
        environment_id=args.environment_id,
        commit_sha=args.commit_sha,
    )
    controller = Controller(telemetry)
    if args.command == "connect":
        out = controller.connect(args.config, args.key)
    elif args.command == "check":
        out = controller.check()
    elif args.command == "disconnect":
        out = controller.disconnect()
    else:
        out = controller.apply_config(args.config, args.approved)
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
