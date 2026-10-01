"""Disposable G01 topology: build, operate and destroy. Runs in the root namespace.

    python3 -m shield.topology up | down | verify-clean

  cgshield-client  (cg-veth-c 192.0.2.2/30, cgwg-c 10.77.0.2/24, network lock)
        |  veth, TEST-NET-1 only; no default route in either namespace
  cgshield-gateway (cg-veth-g 192.0.2.1/30, cgwg-g 10.77.0.1/24, UDP 51820)
        services bound to 10.77.0.1 only: HTTP 8080, DNS 5353, health 18080

Nothing is published in the root namespace. Keys are generated per environment
by `wg genkey`, kept in a 0700 directory as 0600 files, and deleted on teardown.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from shield import common
from shield.common import (
    DNS_PORT,
    HEALTH_PORT,
    HTTP_PORT,
    NS_CLIENT,
    NS_GATEWAY,
    ROOT,
    TUNNEL_NET,
    UNDERLAY_CLIENT,
    UNDERLAY_GATEWAY,
    UNDERLAY_PREFIX,
    VETH_CLIENT,
    VETH_GATEWAY,
    WG_CLIENT,
    WG_GATEWAY,
    WG_PORT,
    sh,
)

REPO = Path(__file__).resolve().parents[1]

# Client-side network lock. Tunnel-range traffic may leave only through the
# tunnel interface, and DNS may leave only through the tunnel interface.
LOCK_RULES = (
    ("OUTPUT", "-o", "lo", "-j", "ACCEPT"),
    ("OUTPUT", "-d", TUNNEL_NET, "-o", WG_CLIENT, "-j", "ACCEPT"),
    ("OUTPUT", "-d", TUNNEL_NET, "-j", "REJECT"),
    ("OUTPUT", "-p", "udp", "--dport", "53", "!", "-o", WG_CLIENT, "-j", "REJECT"),
    ("OUTPUT", "-p", "udp", "--dport", str(DNS_PORT), "!", "-o", WG_CLIENT, "-j", "REJECT"),
    ("OUTPUT", "-p", "tcp", "--dport", "53", "!", "-o", WG_CLIENT, "-j", "REJECT"),
)
ROUTE_LOCK = LOCK_RULES[2]
DNS_LOCK = LOCK_RULES[4]

SERVICES = {
    "http": [sys.executable, "-m", "http.server", str(HTTP_PORT), "--bind", common.TUNNEL_GATEWAY,
             "--directory", str(ROOT / "www")],
    "dns": [sys.executable, str(REPO / "shield/scripts/dns_server.py"), common.TUNNEL_GATEWAY,
            str(DNS_PORT)],
    "health": [sys.executable, "-m", "shield.gateway.health", common.TUNNEL_GATEWAY,
               str(HEALTH_PORT)],
    # Only started by DNS-03: a resolver on the underlay, which the lock must refuse.
    "rogue-dns": [sys.executable, str(REPO / "shield/scripts/dns_server.py"), UNDERLAY_GATEWAY,
                  str(DNS_PORT)],
}
SERVICE_PORTS = {"http": ("tcp", HTTP_PORT), "dns": ("udp", DNS_PORT),
                 "health": ("tcp", HEALTH_PORT), "rogue-dns": ("udp", DNS_PORT)}


# -- keys -------------------------------------------------------------------

def _write_private(path: Path, value: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(value + "\n")


def generate_keypair(name: str) -> str:
    """Write ROOT/<name>.key (0600) and ROOT/<name>.pub. Returns the public key."""
    private = subprocess.run(["wg", "genkey"], text=True, capture_output=True, check=True).stdout
    public = subprocess.run(["wg", "pubkey"], input=private, text=True, capture_output=True,
                            check=True).stdout.strip()
    _write_private(ROOT / f"{name}.key", private.strip())
    (ROOT / f"{name}.pub").write_text(public + "\n", encoding="utf-8")
    del private
    return public


def public_key(name: str) -> str:
    return (ROOT / f"{name}.pub").read_text(encoding="utf-8").strip()


def fingerprint(public: str) -> str:
    return hashlib.sha256(public.encode()).hexdigest()


# -- gateway ------------------------------------------------------------------

def gateway_configure(key_file: Path, peers: list[str]) -> bool:
    """Bring up the gateway tunnel. On any rejected setting, remove it: fail closed."""
    common.wg_link_del(WG_GATEWAY, NS_GATEWAY)
    common.wg_link_add(WG_GATEWAY, NS_GATEWAY)
    args = ["wg", "set", WG_GATEWAY, "private-key", str(key_file), "listen-port", str(WG_PORT)]
    for peer in peers:
        args += ["peer", peer, "allowed-ips", f"{common.TUNNEL_CLIENT}/32"]
    if sh(args, ns=NS_GATEWAY, check=False).returncode != 0:
        common.wg_link_del(WG_GATEWAY, NS_GATEWAY)
        return False
    sh(["ip", "addr", "add", f"{common.TUNNEL_GATEWAY}/24", "dev", WG_GATEWAY], ns=NS_GATEWAY)
    sh(["ip", "link", "set", WG_GATEWAY, "up"], ns=NS_GATEWAY)
    return True


def gateway_down() -> None:
    common.wg_link_del(WG_GATEWAY, NS_GATEWAY)


def gateway_restart() -> bool:
    """Stop and restart the gateway tunnel and its services with the same key and allowlist."""
    for name in ("http", "dns", "health"):
        service_stop(name)
    gateway_down()
    ok = gateway_configure(ROOT / "gateway.key", [public_key("client")])
    if ok:
        for name in ("http", "dns", "health"):
            service_start(name)
    return ok


def revoke(peer: str) -> None:
    sh(["wg", "set", WG_GATEWAY, "peer", peer, "remove"], ns=NS_GATEWAY)


def allow(peer: str) -> None:
    sh(["wg", "set", WG_GATEWAY, "peer", peer, "allowed-ips", f"{common.TUNNEL_CLIENT}/32"],
       ns=NS_GATEWAY)


def underlay(state: str) -> None:
    sh(["ip", "link", "set", VETH_GATEWAY, state], ns=NS_GATEWAY)


# -- services -----------------------------------------------------------------

def _listening(ns: str, proto: str, port: int) -> bool:
    flag = "-lntH" if proto == "tcp" else "-lnuH"
    out = sh(["ss", flag], ns=ns, check=False).stdout
    return any(line.split()[3].endswith(f":{port}") for line in out.splitlines() if len(line.split()) > 3)


def service_start(name: str) -> None:
    pidfile = ROOT / f"svc-{name}.pid"
    if pidfile.exists():
        return
    log = open(ROOT / f"svc-{name}.log", "ab")  # noqa: SIM115 - handed to the child
    proc = subprocess.Popen(common.ns_prefix(NS_GATEWAY) + SERVICES[name], cwd=REPO,
                            stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                            start_new_session=True)
    log.close()
    pidfile.write_text(str(proc.pid), encoding="utf-8")
    proto, port = SERVICE_PORTS[name]
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"service {name} exited")
        if _listening(NS_GATEWAY, proto, port) and (name != "rogue-dns" or _bound(UNDERLAY_GATEWAY)):
            return
        time.sleep(0.05)
    raise RuntimeError(f"service {name} did not start listening")


def _bound(address: str) -> bool:
    out = sh(["ss", "-lnuH"], ns=NS_GATEWAY, check=False).stdout
    return f"{address}:{DNS_PORT}" in out


def service_stop(name: str) -> None:
    pidfile = ROOT / f"svc-{name}.pid"
    if not pidfile.exists():
        return
    pid = int(pidfile.read_text(encoding="utf-8"))
    _kill(pid)
    pidfile.unlink(missing_ok=True)


def _kill(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(100):
            os.kill(pid, 0)
            time.sleep(0.02)
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


# -- client-side network lock and leak simulation ---------------------------------

def lock_rule(rule: tuple[str, ...], action: str) -> None:
    flag = {"add": "-A", "del": "-D"}[action]
    sh(["iptables", flag, *rule], ns=NS_CLIENT)


def lock_rules() -> list[str]:
    out = sh(["iptables", "-S", "OUTPUT"], ns=NS_CLIENT).stdout
    return [line for line in out.splitlines() if line.startswith("-A OUTPUT")]


def leak_route(action: str) -> None:
    """A route for the tunnel range over the underlay: the leak path the lock must refuse."""
    verb = "replace" if action == "add" else "del"
    sh(["ip", "route", verb, TUNNEL_NET, "via", UNDERLAY_GATEWAY, "dev", VETH_CLIENT],
       ns=NS_CLIENT, check=(action == "add"))


# -- lifecycle ------------------------------------------------------------------

def _detect_backend() -> str:
    forced = os.environ.get("SHIELD_WG_BACKEND", "auto")
    if forced in ("kernel", "userspace"):
        return forced
    probe = sh(["ip", "link", "add", "cgwg-probe", "type", "wireguard"], ns=NS_GATEWAY, check=False)
    if probe.returncode == 0:
        sh(["ip", "link", "del", "cgwg-probe"], ns=NS_GATEWAY)
        return "kernel"
    if shutil.which("wireguard-go"):
        return "userspace"
    raise RuntimeError("no WireGuard implementation: kernel module absent and wireguard-go missing")


def up() -> dict[str, object]:
    for tool in ("ip", "wg", "iptables", "ss"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"{tool} is required")
    down()
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, parents=True)
    (ROOT / "www").mkdir()
    (ROOT / "www" / "index.html").write_bytes(common.SERVICE_MARKER + b"\n")
    os.chmod(ROOT / "www", 0o755)
    os.chmod(ROOT / "www" / "index.html", 0o644)

    sh(["ip", "netns", "add", NS_CLIENT])
    sh(["ip", "netns", "add", NS_GATEWAY])
    sh(["ip", "link", "add", VETH_CLIENT, "type", "veth", "peer", "name", VETH_GATEWAY])
    sh(["ip", "link", "set", VETH_CLIENT, "netns", NS_CLIENT])
    sh(["ip", "link", "set", VETH_GATEWAY, "netns", NS_GATEWAY])
    sh(["ip", "addr", "add", f"{UNDERLAY_CLIENT}/{UNDERLAY_PREFIX}", "dev", VETH_CLIENT], ns=NS_CLIENT)
    sh(["ip", "addr", "add", f"{UNDERLAY_GATEWAY}/{UNDERLAY_PREFIX}", "dev", VETH_GATEWAY],
       ns=NS_GATEWAY)
    for ns, veth in ((NS_CLIENT, VETH_CLIENT), (NS_GATEWAY, VETH_GATEWAY)):
        sh(["ip", "link", "set", "lo", "up"], ns=ns)
        sh(["ip", "link", "set", veth, "up"], ns=ns)

    selected = _detect_backend()
    (ROOT / "backend").write_text(selected + "\n", encoding="utf-8")

    client_pub = generate_keypair("client")
    gateway_pub = generate_keypair("gateway")
    if not gateway_configure(ROOT / "gateway.key", [client_pub]):
        raise RuntimeError("gateway rejected its own generated configuration")
    for rule in LOCK_RULES:
        lock_rule(rule, "add")
    for name in ("http", "dns", "health"):
        service_start(name)

    config = {
        "environment": common.ENVIRONMENT,
        "gateway_endpoint": f"{UNDERLAY_GATEWAY}:{WG_PORT}",
        "gateway_identity": "shield-gateway-test",
        "public_key": gateway_pub,
        "tunnel_address": f"{common.TUNNEL_CLIENT}/24",
        "dns_policy": "test-only",
        "network_lock": True,
        "configuration_version": "1",
    }
    (ROOT / "config.json").write_text(json.dumps(config) + "\n", encoding="utf-8")
    safe = {
        "environment": common.ENVIRONMENT,
        "backend": selected,
        "client_public_fingerprint": fingerprint(client_pub),
        "gateway_public_fingerprint": fingerprint(gateway_pub),
    }
    (ROOT / "safe-identities.json").write_text(json.dumps(safe) + "\n", encoding="utf-8")
    return safe


def _stray_processes() -> list[int]:
    """Processes started for this topology that outlived their pid files."""
    markers = (b"cgwg-", b"shield.gateway.health", b"shield/scripts/dns_server.py",
               str(ROOT / "www").encode())
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if not argv or not argv[0]:
            continue
        program = Path(argv[0].decode(errors="ignore")).name
        if program not in ("wireguard-go", "python3", Path(sys.executable).name, "ip"):
            continue
        if any(marker in arg for arg in argv[1:] for marker in markers):
            found.append(int(entry.name))
    return found


def down() -> None:
    if ROOT.exists():
        for pidfile in ROOT.glob("*.pid"):
            try:
                _kill(int(pidfile.read_text(encoding="utf-8")))
            except ValueError:
                pass
    for pid in _stray_processes():
        _kill(pid)
    for ns in (NS_CLIENT, NS_GATEWAY):
        sh(["ip", "netns", "del", ns], check=False)
    sh(["ip", "link", "del", VETH_CLIENT], check=False)
    for iface in (WG_CLIENT, WG_GATEWAY):
        Path(f"/var/run/wireguard/{iface}.sock").unlink(missing_ok=True)
    shutil.rmtree(ROOT, ignore_errors=True)


def verify_clean() -> list[str]:
    """Everything the topology could leave behind. Empty means clean."""
    remaining = []
    namespaces = sh(["ip", "netns", "list"], check=False).stdout.split()
    remaining += [f"namespace {ns}" for ns in (NS_CLIENT, NS_GATEWAY) if ns in namespaces]
    links = sh(["ip", "-o", "link", "show"], check=False).stdout
    remaining += [f"link {name}" for name in (VETH_CLIENT, VETH_GATEWAY, WG_CLIENT, WG_GATEWAY)
                  if f" {name}:" in links or f" {name}@" in links]
    if ROOT.exists():
        remaining.append(f"state directory {ROOT}")
    remaining += [f"socket {iface}" for iface in (WG_CLIENT, WG_GATEWAY)
                  if Path(f"/var/run/wireguard/{iface}.sock").exists()]
    remaining += [f"process {pid}" for pid in _stray_processes()]
    return remaining


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ""
    if command == "up":
        print(json.dumps(up(), sort_keys=True))
        return 0
    if command == "down":
        down()
        return 0
    if command == "verify-clean":
        remaining = verify_clean()
        print(json.dumps({"clean": not remaining, "remaining": remaining}, sort_keys=True))
        return 0 if not remaining else 1
    print("usage: python3 -m shield.topology up|down|verify-clean", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
