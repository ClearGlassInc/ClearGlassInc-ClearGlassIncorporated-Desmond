"""Shared constants and helpers for the disposable G01 test topology.

Everything here operates on synthetic, test-only resources: two Linux network
namespaces joined by a veth pair on TEST-NET-1 (RFC 5737), a WireGuard tunnel on
10.77.0.0/24, and services bound only to the gateway's tunnel address.

The WireGuard data plane is the standard implementation: the kernel module when
the host kernel has one (GitHub's ubuntu-latest), otherwise wireguard-go, the
WireGuard project's userspace implementation, over /dev/net/tun. Both speak the
same protocol and are configured with the same `wg` tool. Nothing here
implements cryptography.
"""

from __future__ import annotations

import base64
import os
import signal
import subprocess
import time
from pathlib import Path

ENVIRONMENT = "isolated-disposable-test"
ROOT = Path(os.environ.get("SHIELD_STATE_DIR", "/tmp/clearglass-shield-test"))

NS_CLIENT = "cgshield-client"
NS_GATEWAY = "cgshield-gateway"
VETH_CLIENT = "cg-veth-c"
VETH_GATEWAY = "cg-veth-g"
WG_CLIENT = "cgwg-c"
WG_GATEWAY = "cgwg-g"

UNDERLAY_GATEWAY = "192.0.2.1"
UNDERLAY_CLIENT = "192.0.2.2"
UNDERLAY_PREFIX = 30
TUNNEL_NET = "10.77.0.0/24"
TUNNEL_GATEWAY = "10.77.0.1"
TUNNEL_CLIENT = "10.77.0.2"
WG_PORT = 51820
HTTP_PORT = 8080
DNS_PORT = 5353
HEALTH_PORT = 18080

SERVICE_MARKER = b"clearglass-shield-g01-synthetic-service"
HANDSHAKE_TIMEOUT_S = 6.0
USERSPACE_ENV = "WG_I_PREFER_BUGGY_USERSPACE_TO_POLISHED_KMOD"


def ns_prefix(ns: str | None) -> list[str]:
    return ["ip", "netns", "exec", ns] if ns else []


def sh(
    args: list[str],
    ns: str | None = None,
    check: bool = True,
    timeout: float = 20,
) -> subprocess.CompletedProcess[str]:
    """Run a command, optionally inside a namespace. Output is captured, never echoed."""
    return subprocess.run(
        ns_prefix(ns) + args, text=True, capture_output=True, check=check, timeout=timeout
    )


def is_wireguard_key(value: str) -> bool:
    """True when value has the shape of a WireGuard key: base64 of exactly 32 bytes."""
    value = value.strip()
    if len(value) != 44 or not value.endswith("="):
        return False
    try:
        return len(base64.b64decode(value, validate=True)) == 32
    except ValueError:
        return False


def backend() -> str:
    """The data plane chosen at bootstrap: 'kernel' or 'userspace'."""
    try:
        return (ROOT / "backend").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def link_exists(iface: str, ns: str | None = None) -> bool:
    return sh(["ip", "link", "show", iface], ns=ns, check=False).returncode == 0


def wg_link_add(iface: str, ns: str | None = None) -> None:
    """Create a WireGuard interface with the backend recorded at bootstrap."""
    if backend() == "kernel":
        sh(["ip", "link", "add", iface, "type", "wireguard"], ns=ns)
        return
    env = dict(os.environ, **{USERSPACE_ENV: "1", "LOG_LEVEL": "error"})
    log = open(ROOT / f"wg-{iface}.log", "ab")  # noqa: SIM115 - handed to the child
    proc = subprocess.Popen(
        ns_prefix(ns) + ["wireguard-go", "-f", iface],
        env=env,
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    log.close()
    (ROOT / f"wg-{iface}.pid").write_text(str(proc.pid), encoding="utf-8")
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if link_exists(iface, ns):
            return
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    raise RuntimeError(f"wireguard-go did not create {iface}")


def wg_link_del(iface: str, ns: str | None = None) -> None:
    """Remove a WireGuard interface and, for userspace, stop its process."""
    pidfile = ROOT / f"wg-{iface}.pid"
    if pidfile.exists():
        pid = int(pidfile.read_text(encoding="utf-8"))
        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(100):
                os.kill(pid, 0)
                time.sleep(0.02)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        pidfile.unlink(missing_ok=True)
    if link_exists(iface, ns):
        sh(["ip", "link", "del", iface], ns=ns, check=False)
    Path(f"/var/run/wireguard/{iface}.sock").unlink(missing_ok=True)


def latest_handshake(iface: str, ns: str | None = None) -> int:
    """Epoch seconds of the most recent handshake on iface, 0 if none."""
    out = sh(["wg", "show", iface, "latest-handshakes"], ns=ns, check=False).stdout
    stamps = [int(line.split()[1]) for line in out.splitlines() if len(line.split()) == 2]
    return max(stamps, default=0)


def transfer(iface: str, ns: str | None = None) -> tuple[int, int]:
    """Bytes received and sent over iface, summed across peers."""
    out = sh(["wg", "show", iface, "transfer"], ns=ns, check=False).stdout
    rx = tx = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            rx += int(parts[1])
            tx += int(parts[2])
    return rx, tx


def peer_count(iface: str, ns: str | None = None) -> int:
    out = sh(["wg", "show", iface, "peers"], ns=ns, check=False).stdout
    return len([line for line in out.splitlines() if line.strip()])
