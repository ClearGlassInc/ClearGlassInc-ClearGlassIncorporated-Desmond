"""Shield G01 test suite. Writes one non-sensitive JSON record per test.

    python3 -m shield.g01_suite cycle N --artifacts DIR --run-id ID
    python3 -m shield.g01_suite static --artifacts DIR --run-id ID

`cycle` builds the topology, runs every runtime test, tears down and verifies
clean (FI-14). `static` runs the repository and scanner checks once per run.

A record's status is PASS only when the measured result matches the expected
one. A test that cannot run is SKIPPED, and SKIPPED is never counted as PASS.
An exception inside a test is a FAIL with its error class recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from shield import common, topology
from shield.client.telemetry import ALLOWED_FIELDS, LABELS
from shield.common import NS_CLIENT, NS_GATEWAY, ROOT, TUNNEL_GATEWAY, sh
from shield.gateway.health import HEALTH_FIELDS
from shield.secret_scan import scan

REPO = Path(__file__).resolve().parents[1]
SCOPE_LIMIT = "Linux network-namespace G01 topology only"


def commit_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True,
                          check=True).stdout.strip()


class Recorder:
    def __init__(self, outdir: Path, run_id: str, cycle: str):
        self.outdir = outdir
        self.tests = outdir / "tests"
        self.tests.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.cycle = cycle
        self.commit = commit_sha()
        self.environment_id = f"shield-g01-{self.commit[:7]}-{run_id}"
        self.telemetry = outdir / "telemetry.jsonl"

    def write(self, test_id: str, expected: str, actual: object, status: str,
              artifact: dict[str, object] | None = None, limitations: tuple[str, ...] = ()) -> str:
        reference = ""
        if artifact is not None:
            path = self.outdir / "detail" / f"{test_id}.json"
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            reference = str(path.relative_to(self.outdir.parent))
        record = {
            "test_id": test_id,
            "cycle": self.cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "environment_id": self.environment_id,
            "run_id": self.run_id,
            "commit_sha": self.commit,
            "expected_result": expected,
            "actual_result": actual if isinstance(actual, str) else json.dumps(actual, sort_keys=True),
            "status": status,
            "artifact_reference": reference,
            "limitations": list(limitations),
        }
        (self.tests / f"{test_id}.json").write_text(json.dumps(record, indent=2) + "\n",
                                                   encoding="utf-8")
        print(f"  {status:7} {test_id:10} {expected}", flush=True)
        return status

    def run(self, test_id: str, expected: str, fn: Callable[[], tuple[bool | None, object, dict | None]],
            limitations: tuple[str, ...] = (SCOPE_LIMIT,)) -> str:
        try:
            ok, actual, detail = fn()
        except Exception as exc:  # noqa: BLE001 - a crashed test is a failed test
            return self.write(test_id, expected, f"exception: {type(exc).__name__}: {exc}"[:300],
                              "FAIL", None, limitations)
        status = "SKIPPED" if ok is None else ("PASS" if ok else "FAIL")
        return self.write(test_id, expected, actual, status, detail, limitations)


# -- helpers ------------------------------------------------------------------

class Env:
    def __init__(self, rec: Recorder):
        self.rec = rec
        self.test_id = "unset"

    def client(self, command: str, config: Path | None = None, key: Path | None = None,
               candidate: Path | None = None) -> dict[str, object]:
        args = [sys.executable, "-m", "shield.client.controller", command,
                "--telemetry", str(self.rec.telemetry), "--test-id", self.test_id,
                "--run-id", self.rec.run_id, "--environment-id", self.rec.environment_id,
                "--commit-sha", self.rec.commit[:12]]
        if command == "connect":
            args += ["--config", str(config or ROOT / "config.json"),
                     "--key", str(key or ROOT / "client.key")]
        if command == "apply-config":
            args += ["--config", str(candidate), "--approved", str(ROOT / "config.json")]
        out = subprocess.run(common.ns_prefix(NS_CLIENT) + args, cwd=REPO, text=True,
                             capture_output=True, check=True, timeout=60)
        return json.loads(out.stdout)

    def probe(self, *args: object) -> dict[str, object]:
        out = subprocess.run(common.ns_prefix(NS_CLIENT) +
                             [sys.executable, "-m", "shield.probes", *map(str, args)],
                             cwd=REPO, text=True, capture_output=True, check=True, timeout=30)
        return json.loads(out.stdout)

    def protected(self) -> bool:
        """True if the protected synthetic service answers from the client namespace."""
        return bool(self.probe("http", TUNNEL_GATEWAY, common.HTTP_PORT).get("reachable"))

    def healthy(self) -> bool:
        return self.client("connect")["final_state"] == "HEALTHY"


def _config_variant(name: str, **changes: object) -> Path:
    base = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    for key, value in changes.items():
        if value is _DELETE:
            base.pop(key, None)
        else:
            base[key] = value
    path = ROOT / f"config-{name}.json"
    path.write_text(json.dumps(base) + "\n", encoding="utf-8")
    return path


_DELETE = object()

# Each case is (case id, config changes, expected state, expected error class).
CONFIG_CASES = (
    ("CFG-01", {"tunnel_address": _DELETE}, "CONFIG_FAILURE", "missing_field"),
    ("CFG-02", {"environment": "staging"}, "CONFIG_FAILURE", "non_test_environment"),
    ("CFG-03", {"gateway_endpoint": "203.0.113.10:51820"}, "CONFIG_FAILURE", "non_test_endpoint"),
    ("CFG-04", {"tunnel_address": "10.0.0.2/24"}, "CONFIG_FAILURE", "non_test_cidr"),
    ("CFG-05", {"public_key": "not-a-wireguard-key"}, "CONFIG_FAILURE", "malformed_public_key"),
    ("CFG-06", {"configuration_version": "2"}, "CONFIG_FAILURE", "unsupported_version"),
    ("CFG-07", {"network_lock": False}, "CONFIG_FAILURE", "network_lock_missing"),
    ("CFG-08", {"debug": True}, "CONFIG_FAILURE", "unexpected_field"),
)


# -- runtime cycle ------------------------------------------------------------------

def run_cycle(rec: Recorder) -> None:
    env = Env(rec)
    try:
        _cycle_tests(rec, env)
    finally:
        topology.down()
    remaining = topology.verify_clean()
    rec.write("FI-14", "teardown removes namespaces, links, sockets, processes, keys and state",
              {"remaining": remaining, "state_dir_exists": ROOT.exists()},
              "PASS" if not remaining else "FAIL", {"remaining": remaining})


def _cycle_tests(rec: Recorder, env: Env) -> None:
    def t(test_id: str, expected: str, fn: Callable[[], tuple], **kw: object) -> str:
        env.test_id = test_id
        return rec.run(test_id, expected, fn, **kw)

    safe: dict[str, object] = {}

    def boot():
        safe.update(topology.up())
        gw_listen = sh(["ss", "-lntuH"], ns=NS_GATEWAY).stdout.split("\n")
        listeners = sorted({line.split()[4] for line in gw_listen if len(line.split()) > 4})
        rules = topology.lock_rules()
        checks = {
            "namespaces": all(ns in sh(["ip", "netns", "list"]).stdout for ns in (NS_CLIENT, NS_GATEWAY)),
            "gateway_tunnel": common.link_exists(common.WG_GATEWAY, NS_GATEWAY),
            "gateway_peers": common.peer_count(common.WG_GATEWAY, NS_GATEWAY),
            "lock_rules": len(rules),
            "services_bound": listeners,
        }
        expected_listeners = {f"{TUNNEL_GATEWAY}:{p}" for p in (common.HTTP_PORT, common.DNS_PORT,
                                                                 common.HEALTH_PORT)}
        ok = (checks["namespaces"] and checks["gateway_tunnel"] and checks["gateway_peers"] == 1
              and checks["lock_rules"] == len(topology.LOCK_RULES)
              and expected_listeners <= set(listeners))
        return ok, {k: v for k, v in checks.items() if k != "services_bound"}, {
            **safe, **checks, "lock_rule_text": rules}

    if t("BOOT-01", "disposable client and gateway namespaces, gateway tunnel with 1 allowed peer, "
         "lock rules installed, services bound to the tunnel address", boot) != "PASS":
        return

    def keys():
        modes = {name: oct((ROOT / f"{name}.key").stat().st_mode & 0o777) for name in ("client", "gateway")}
        shapes = {name: common.is_wireguard_key((ROOT / f"{name}.key").read_text()) for name in
                  ("client", "gateway")}
        dir_mode = oct(ROOT.stat().st_mode & 0o777)
        outside_repo = REPO not in ROOT.parents
        ok = (all(m == "0o600" for m in modes.values()) and all(shapes.values())
              and dir_mode == "0o700" and outside_repo)
        actual = {"key_modes": modes, "key_shape_valid": shapes, "state_dir_mode": dir_mode,
                  "state_dir_outside_repo": outside_repo,
                  "exported": "public-key sha256 fingerprints only"}
        return ok, actual, {**actual, "client_public_fingerprint": safe["client_public_fingerprint"],
                            "gateway_public_fingerprint": safe["gateway_public_fingerprint"]}

    t("KEY-01", "keys generated by wg genkey per environment, 0600 in a 0700 directory outside "
      "the repository; only fingerprints exported", keys)

    def dns_before():
        r = env.probe("dns", TUNNEL_GATEWAY, common.DNS_PORT, "service.shield.test")
        return r["answered"] is False, {"test_dns_answered": r["answered"],
                                        "dns_policy_state": "not_asserted"}, None

    t("DNS-01", "before the tunnel, the test resolver is unreachable and DNS policy is not "
      "asserted", dns_before)

    def lock_control():
        topology.leak_route("add")
        try:
            topology.lock_rule(topology.ROUTE_LOCK, "del")
            without_lock = env.protected()
            topology.lock_rule(topology.ROUTE_LOCK, "add")
            with_lock = env.protected()
        finally:
            topology.leak_route("del")
        rules_restored = len(topology.lock_rules()) == len(topology.LOCK_RULES)
        ok = without_lock and not with_lock and rules_restored
        return ok, {"leak_route_reachable_without_lock": without_lock,
                    "leak_route_reachable_with_lock": with_lock,
                    "lock_rules_restored": rules_restored}, None

    t("LOCK-CTRL", "control: with a leak route over the underlay, the protected service is "
      "reachable without the lock rule and blocked with it", lock_control)

    def tunnel_up():
        r = env.client("connect")
        stamp = common.latest_handshake(common.WG_CLIENT, NS_CLIENT)
        age = round(time.time() - stamp, 1) if stamp else None
        ok = r["final_state"] == "HEALTHY" and stamp > 0
        return ok, {"final_state": r["final_state"], "handshake_age_s": age}, {
            "state_path": r["path"], "handshake_age_s": age,
            "gateway_peer_count": common.peer_count(common.WG_GATEWAY, NS_GATEWAY)}

    t("TUN-01", "valid client completes a WireGuard handshake and reaches HEALTHY", tunnel_up)

    def traffic():
        r = env.probe("http", TUNNEL_GATEWAY, common.HTTP_PORT)
        rx, tx = common.transfer(common.WG_CLIENT, NS_CLIENT)
        ok = r.get("status") == 200 and r.get("marker") is True and rx > 0 and tx > 0
        return ok, {"status": r.get("status"), "synthetic_marker": r.get("marker"),
                    "tunnel_rx_bytes_positive": rx > 0, "tunnel_tx_bytes_positive": tx > 0}, None

    t("TUN-02", "synthetic HTTP request crosses the tunnel; tunnel byte counters increase", traffic)
    def allowed_when_healthy():
        reachable = env.protected()
        return reachable, {"protected_reachable": reachable}, None

    t("LOCK-01", "tunnel healthy: protected synthetic route allowed", allowed_when_healthy)

    def dns_policy():
        answers = {name: env.probe("dns", TUNNEL_GATEWAY, common.DNS_PORT, name) for name in
                   ("service.shield.test", "health.shield.test", "blocked.shield.test")}
        ok = (answers["service.shield.test"].get("answer") == TUNNEL_GATEWAY
              and answers["health.shield.test"].get("answer") == TUNNEL_GATEWAY
              and answers["blocked.shield.test"].get("rcode") == 3)
        actual = {name: {"rcode": a.get("rcode"), "answer_class": "test-gateway" if a.get("answer")
                         == TUNNEL_GATEWAY else a.get("answer")} for name, a in answers.items()}
        return ok, actual, {"resolver": "shield-dns-test (10.77.0.1:5353, via tunnel)", **actual}

    t("DNS-02", "service and health resolve through the test resolver over the tunnel; "
      "blocked.shield.test is NXDOMAIN", dns_policy)

    def gateway_health():
        r = env.probe("http", TUNNEL_GATEWAY, common.HEALTH_PORT, "/health")
        body = r.get("health", {})
        ok = (r.get("status") == 200 and set(body) == set(HEALTH_FIELDS) and body.get("peer_count") == 1
              and body.get("production_status") == "not_production" and body.get("test_mode") is True)
        return ok, {"status": r.get("status"), "fields": sorted(body)}, {"health": body}

    t("GW-01", "gateway health answers inside the test network with only the allowed fields",
      gateway_health)

    def debug_endpoints():
        paths = ("/debug", "/debug/pprof", "/metrics", "/config", "/status")
        codes = {p: env.probe("http", TUNNEL_GATEWAY, common.HEALTH_PORT, p).get("status") for p in paths}
        underlay = {str(port): env.probe("tcp", common.UNDERLAY_GATEWAY, port)["reachable"] for port in
                    (common.HEALTH_PORT, common.HTTP_PORT)}
        ok = all(c == 404 for c in codes.values()) and not any(underlay.values())
        return ok, {"debug_paths": codes, "reachable_on_underlay": underlay}, None

    t("FI-13", "debug and metrics paths are 404; health and service are not reachable on the "
      "underlay", debug_endpoints)

    def client_restart():
        down = env.client("disconnect")
        blocked_while_down = not env.protected()
        up = env.client("connect")
        ok = down["final_state"] == "DISCONNECTED" and blocked_while_down and up["final_state"] == "HEALTHY"
        return ok, {"after_disconnect": down["final_state"], "protected_while_down": not blocked_while_down,
                    "after_reconnect": up["final_state"]}, None

    t("FI-09", "client restart: disconnect, protected route blocked, reconnect to HEALTHY",
      client_restart)

    def interruption():
        sh(["ip", "link", "del", common.WG_CLIENT], ns=NS_CLIENT)
        r = env.client("check")
        return (r["failure_state"] == "TUNNEL_FAILURE" and r["final_state"] == "NETWORK_LOCK_ACTIVE",
                {"failure_state": r["failure_state"], "final_state": r["final_state"]}, None)

    t("FI-06", "tunnel interface removed mid-session: client detects TUNNEL_FAILURE and the lock "
      "stays active", interruption)

    def locked_with_leak():
        topology.leak_route("add")
        try:
            reachable = env.protected()
        finally:
            topology.leak_route("del")
        return not reachable, {"protected_reachable_via_leak_route": reachable}, None

    t("LOCK-02", "tunnel interrupted: protected route blocked even with a leak route present",
      locked_with_leak)

    def datapath_killed():
        if not env.healthy():
            return False, "could not reach HEALTHY before the test", None
        if common.backend() == "userspace":
            pid = int((ROOT / f"wg-{common.WG_CLIENT}.pid").read_text())
            os.kill(pid, 9)
            how = "SIGKILL to the client wireguard-go process"
        else:
            sh(["ip", "link", "set", common.WG_CLIENT, "down"], ns=NS_CLIENT)
            how = "client WireGuard interface set down"
        time.sleep(0.5)
        topology.leak_route("add")
        try:
            reachable = env.protected()
        finally:
            topology.leak_route("del")
        env.client("disconnect")
        return not reachable, {"method": how, "protected_reachable_via_leak_route": reachable}, None

    t("LOCK-04", "client data plane stopped: no protected-route access, leak route present",
      datapath_killed)

    def gateway_unavailable():
        topology.underlay("down")
        try:
            r = env.client("connect")
            blocked = not env.protected()
        finally:
            topology.underlay("up")
        time.sleep(0.5)
        recovered = env.healthy()
        ok = r["failure_state"] == "GATEWAY_UNAVAILABLE" and blocked and recovered
        return ok, {"failure_state": r["failure_state"], "protected_blocked": blocked,
                    "recovered_after_restore": recovered}, None

    t("FI-01", "gateway host unavailable: GATEWAY_UNAVAILABLE, protected route blocked",
      gateway_unavailable)
    t("LOCK-03", "gateway unavailable: protected route blocked (measured in FI-01)",
      lambda: _from(rec, "FI-01", "protected_blocked"))

    def invalid_peer():
        topology.generate_keypair("rogue")
        try:
            r = env.client("connect", key=ROOT / "rogue.key")
            blocked = not env.protected()
        finally:
            for suffix in ("key", "pub"):
                (ROOT / f"rogue.{suffix}").unlink(missing_ok=True)
        ok = r["failure_state"] in ("HANDSHAKE_FAILURE", "AUTH_FAILURE") and blocked
        return ok, {"failure_state": r["failure_state"], "protected_blocked": blocked}, None

    t("FI-02", "client key not on the gateway allowlist: AUTH_FAILURE or HANDSHAKE_FAILURE",
      invalid_peer)

    def revoked():
        if not env.healthy():
            return False, "could not reach HEALTHY before the test", None
        client_pub = topology.public_key("client")
        topology.revoke(client_pub)
        try:
            r = env.client("connect")
            blocked = not env.protected()
        finally:
            topology.allow(client_pub)
        recovered = env.healthy()
        ok = r["failure_state"] in ("REVOKED", "HANDSHAKE_FAILURE") and blocked and recovered
        return ok, {"failure_state": r["failure_state"], "protected_blocked": blocked,
                    "recovered_after_reinstating_peer": recovered}, None

    t("FI-03", "revoked peer: REVOKED or HANDSHAKE_FAILURE, protected route blocked", revoked)

    def dns_down():
        topology.service_stop("dns")
        try:
            r = env.client("connect")
            blocked = not env.protected()
        finally:
            topology.service_start("dns")
        recovered = env.healthy()
        ok = r["failure_state"] == "DNS_FAILURE" and blocked and recovered
        return ok, {"failure_state": r["failure_state"], "error_class": r["error_class"],
                    "protected_blocked": blocked, "recovered": recovered}, None

    t("FI-07", "test resolver unavailable: DNS_FAILURE", dns_down)

    def dns_config():
        r = env.client("connect", config=_config_variant("dns", dns_policy="198.51.100.53"))
        blocked = not env.protected()
        ok = (r["failure_state"] == "DNS_FAILURE" and r["error_class"] == "dns_policy_rejected"
              and blocked)
        return ok, {"failure_state": r["failure_state"], "error_class": r["error_class"],
                    "protected_blocked": blocked}, None

    t("DNS-04", "configuration naming an external resolver: DNS_FAILURE, no tunnel", dns_config)

    def malformed_configs():
        results = {}
        for case_id, changes, state, error_class in CONFIG_CASES:
            r = env.client("connect", config=_config_variant(case_id, **changes))
            results[case_id] = {"failure_state": r["failure_state"], "error_class": r["error_class"],
                                "pass": r["failure_state"] == state and r["error_class"] == error_class}
        broken = ROOT / "config-unreadable.json"
        broken.write_text("{not json", encoding="utf-8")
        r = env.client("connect", config=broken)
        results["CFG-09"] = {"failure_state": r["failure_state"], "error_class": r["error_class"],
                             "pass": r["failure_state"] == "CONFIG_FAILURE"}
        ok = all(case["pass"] for case in results.values())
        return ok, {k: v["failure_state"] for k, v in results.items()}, {"cases": results}

    t("FI-04", "malformed client configurations are rejected with CONFIG_FAILURE", malformed_configs)
    def blocked_after_invalid_config():
        reachable = env.protected()
        return not reachable, {"protected_reachable": reachable}, None

    t("LOCK-05", "invalid configuration: protected route blocked", blocked_after_invalid_config)

    def rollback():
        approved = ROOT / "config.json"
        before = hashlib.sha256(approved.read_bytes()).hexdigest()
        bad = _config_variant("rollback", gateway_endpoint="203.0.113.10:51820")
        r = env.client("apply-config", candidate=bad)
        after = hashlib.sha256(approved.read_bytes()).hexdigest()
        reconnected = env.healthy()
        ok = r.get("adopted") is False and before == after and reconnected
        return ok, {"candidate_adopted": r.get("adopted"), "approved_config_unchanged": before == after,
                    "reconnected_with_approved": reconnected}, {"state_path": r["path"]}

    t("FI-10", "rejected configuration change rolls back to the approved configuration", rollback)

    def bad_gateway_config():
        bad_key = ROOT / "bad-gateway.key"
        topology._write_private(bad_key, "not-a-wireguard-key")
        accepted = topology.gateway_configure(bad_key, [topology.public_key("client")])
        bad_key.unlink()
        tunnel_present = common.link_exists(common.WG_GATEWAY, NS_GATEWAY)
        r = env.client("connect")
        restored = topology.gateway_restart()
        recovered = env.healthy()
        ok = (not accepted and not tunnel_present and r["failure_state"] == "HANDSHAKE_FAILURE"
              and restored and recovered)
        return ok, {"gateway_accepted_bad_config": accepted, "gateway_tunnel_left_up": tunnel_present,
                    "client_failure_state": r["failure_state"], "recovered": recovered}, None

    t("FI-05", "invalid gateway configuration: gateway refuses it and leaves no tunnel", bad_gateway_config)

    def gateway_restart():
        if not env.healthy():
            return False, "could not reach HEALTHY before the test", None
        for name in ("http", "dns", "health"):
            topology.service_stop(name)
        topology.gateway_down()
        during = env.client("check")
        early = env.client("connect")
        restored = topology.gateway_restart()
        after = env.client("connect")
        dns = env.probe("dns", TUNNEL_GATEWAY, common.DNS_PORT, "service.shield.test")
        ok = (during["failure_state"] == "TUNNEL_FAILURE" and early["failure_state"] == "HANDSHAKE_FAILURE"
              and restored and after["final_state"] == "HEALTHY" and dns.get("answer") == TUNNEL_GATEWAY)
        return ok, {"check_during_outage": during["failure_state"],
                    "connect_during_outage": early["failure_state"],
                    "connect_after_recovery": after["final_state"],
                    "dns_after_recovery": dns.get("answer") == TUNNEL_GATEWAY}, None

    t("FI-08", "gateway restart: client cannot connect during the outage and reconnects only after "
      "valid recovery", gateway_restart)
    t("DNS-05", "DNS policy restored after gateway restart (measured in FI-08)",
      lambda: _from(rec, "FI-08", "dns_after_recovery"))

    def dns_bypass():
        env.client("disconnect")
        topology.service_start("rogue-dns")
        try:
            locked = env.probe("dns", common.UNDERLAY_GATEWAY, common.DNS_PORT, "service.shield.test")
            topology.lock_rule(topology.DNS_LOCK, "del")
            try:
                unlocked = env.probe("dns", common.UNDERLAY_GATEWAY, common.DNS_PORT, "service.shield.test")
            finally:
                topology.lock_rule(topology.DNS_LOCK, "add")
            tunnel_dns = env.probe("dns", TUNNEL_GATEWAY, common.DNS_PORT, "service.shield.test")
        finally:
            topology.service_stop("rogue-dns")
        ok = not locked["answered"] and unlocked["answered"] and not tunnel_dns["answered"]
        return ok, {"underlay_resolver_answered_with_lock": locked["answered"],
                    "underlay_resolver_answered_without_lock_control": unlocked["answered"],
                    "test_resolver_answered_without_tunnel": tunnel_dns["answered"]}, None

    t("DNS-03", "tunnel down: a resolver on the underlay is refused by the lock (control: it "
      "answers without the lock rule)", dns_bypass)

    def egress():
        external = {target: env.probe("tcp", target, port)["reachable"] for target, port in
                    (("198.51.100.10", 443), ("203.0.113.10", 80))}
        routes = {ns: sh(["ip", "route", "show", "default"], ns=ns).stdout.strip() for ns in
                  (NS_CLIENT, NS_GATEWAY)}
        forwarding = sh(["cat", "/proc/sys/net/ipv4/ip_forward"], ns=NS_GATEWAY).stdout.strip()
        links = {ns: sorted(line.split(":")[1].strip().split("@")[0] for line in
                            sh(["ip", "-o", "link", "show"], ns=ns).stdout.splitlines()) for ns in
                 (NS_CLIENT, NS_GATEWAY)}
        allowed_links = {NS_CLIENT: {"lo", common.VETH_CLIENT, common.WG_CLIENT},
                         NS_GATEWAY: {"lo", common.VETH_GATEWAY, common.WG_GATEWAY}}
        ok = (not any(external.values()) and not any(routes.values()) and forwarding == "0"
              and all(set(links[ns]) <= allowed_links[ns] for ns in links))
        return ok, {"external_targets_reachable": external, "default_routes": routes,
                    "gateway_ip_forward": forwarding, "interfaces": links}, None

    t("FI-11", "no route out of the test topology: external targets unreachable, no default "
      "routes, gateway does not forward", egress)

    def exposure():
        listeners = sh(["ss", "-lntuH"]).stdout.splitlines()
        hits = [line.split()[4] for line in listeners if len(line.split()) > 4 and (
            line.split()[4].startswith(("10.77.0.", "192.0.2.")) or line.split()[4].endswith(":51820"))]
        root_links = sh(["ip", "-o", "link", "show"]).stdout
        leaked_links = [n for n in (common.VETH_CLIENT, common.VETH_GATEWAY, common.WG_CLIENT,
                                    common.WG_GATEWAY) if f" {n}:" in root_links or f" {n}@" in root_links]
        ok = not hits and not leaked_links
        return ok, {"root_namespace_test_listeners": hits, "root_namespace_test_links": leaked_links}, None

    t("SEC-04", "nothing from the topology is published in the root namespace", exposure)

    def key_leak():
        secrets = [(ROOT / f"{n}.key").read_text().strip() for n in ("client", "gateway")]
        places = [rec.outdir, *ROOT.glob("*.log")]
        hits = 0
        for place in places:
            files = [place] if place.is_file() else [p for p in place.rglob("*") if p.is_file()]
            for path in files:
                text = path.read_text(encoding="utf-8", errors="ignore")
                hits += sum(text.count(s) for s in secrets)
        del secrets
        return hits == 0, {"private_key_occurrences_in_artifacts_and_logs": hits}, None

    t("SEC-02", "generated private keys appear nowhere in artifacts, telemetry or logs", key_leak)

    def artifact_scan():
        findings = scan([rec.outdir])
        return not findings, {"findings": len(findings)}, {"findings": findings}

    t("SEC-06", "secret scan of this cycle's artifacts finds nothing", artifact_scan)

    def telemetry_allowlist():
        lines = rec.telemetry.read_text(encoding="utf-8").splitlines() if rec.telemetry.exists() else []
        events = [json.loads(line) for line in lines]
        bad_fields = sorted({k for e in events for k in e if k not in ALLOWED_FIELDS})
        bad_labels = [e for e in events if any(e.get(k) != v for k, v in LABELS.items())]
        states = sorted({e["state"] for e in events})
        ok = bool(events) and not bad_fields and not bad_labels
        return ok, {"events": len(events), "fields_outside_allowlist": bad_fields,
                    "events_missing_test_labels": len(bad_labels)}, {"states_observed": states}

    t("SEC-07", "every telemetry event uses only allowlisted fields and carries the TEST_ONLY "
      "labels", telemetry_allowlist)


def _from(rec: Recorder, source: str, field: str) -> tuple[bool, object, None]:
    record = json.loads((rec.tests / f"{source}.json").read_text())
    if record["status"] == "SKIPPED":
        return None, f"{source} skipped", None
    actual = json.loads(record["actual_result"]) if record["actual_result"].startswith("{") else {}
    value = actual.get(field)
    return record["status"] == "PASS" and value is True, {field: value, "source": source}, None


# -- static checks ------------------------------------------------------------------

def run_static(rec: Recorder) -> None:
    def tree():
        paths = ["shield", ".github/workflows/shield-g01-mvp.yml"]
        changes = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO, text=True,
                                 capture_output=True, check=True).stdout.splitlines()
        return not changes, {"commit": rec.commit, "uncommitted_changes": len(changes)}, None

    rec.run("TREE-01", "the code under test is exactly the recorded commit (no uncommitted "
            "changes in shield/ or its workflow)", tree, limitations=())

    def unit():
        out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                              "shield/tests"], cwd=REPO, text=True, capture_output=True)
        summary = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
        counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|skipped|error)", summary)}
        ok = out.returncode == 0 and counts.get("failed", 0) == 0 and counts.get("passed", 0) > 0
        return ok, {"summary": summary, **counts}, None

    rec.run("UNIT-01", "unit tests in shield/tests pass", unit, limitations=())

    def repo_scan():
        findings = scan([REPO / "shield"])
        return not findings, {"findings": len(findings)}, {"findings": findings}

    rec.run("SEC-01", "secret scan of shield/ finds no keys, PEM blocks or live payment secrets",
            repo_scan, limitations=())

    def planted():
        tmp = Path(tempfile.mkdtemp(prefix="shield-fi12-"))
        try:
            key = subprocess.run(["wg", "genkey"], text=True, capture_output=True, check=True).stdout
            (tmp / "planted.conf").write_text("".join(("[Interface]\nPrivate", "Key = ", key)),
                                              encoding="utf-8")
            (tmp / "planted.json").write_text(json.dumps({"private_key": key.strip()}), encoding="utf-8")
            del key
            findings = scan([tmp])
            exit_code = subprocess.run([sys.executable, "-m", "shield.secret_scan", str(tmp)],
                                       cwd=REPO, capture_output=True).returncode
        finally:
            shutil.rmtree(tmp)
        rules = sorted({f["rule"] for f in findings})
        ok = exit_code == 1 and {"wireguard-private-key-line", "private-key-field"} <= set(rules)
        return ok, {"scanner_exit_code": exit_code, "rules_triggered": rules,
                    "planted_fixture_removed": not tmp.exists()}, None

    rec.run("FI-12", "a planted private key in a fixture makes the secret scanner fail", planted,
            limitations=())

    def exclusions():
        ignored = {name: subprocess.run(["git", "check-ignore", "-q", name], cwd=REPO).returncode == 0
                   for name in ("shield/client.key", "shield/.env", "artifacts/shield-g01/x.json")}
        tracked = subprocess.run(["git", "ls-files"], cwd=REPO, text=True, capture_output=True,
                                 check=True).stdout.splitlines()
        tracked_keys = [p for p in tracked if p.endswith(".key") or Path(p).name == ".env"]
        ok = all(ignored.values()) and not tracked_keys
        return ok, {"gitignored": ignored, "tracked_key_or_env_files": tracked_keys}, None

    rec.run("SEC-03", "*.key, .env and the artifact directory are git-ignored; none is tracked",
            exclusions, limitations=())

    def boundary():
        markers = ["".join(parts) for parts in (("sk_", "live_"), ("STRIPE_", "SECRET"),
                                                    ("api.", "stripe.com"), ("buy.", "stripe.com"),
                                                    ("checkout.", "stripe.com"))]
        hits = []
        for path in sorted((REPO / "shield").rglob("*")):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                hits += [f"{path.relative_to(REPO)}: {m}" for m in markers if m in text]
        return not hits, {"stripe_or_payment_references": hits}, None

    rec.run("SEC-08", "no Stripe key, API host or checkout reference anywhere in shield/", boundary,
            limitations=())

    rec.run("SEC-09", "dependency vulnerability audit",
            lambda: (None, "not run: shield/ imports only the Python standard library; WireGuard "
                     "tools come from the Ubuntu archive; no offline auditor is available", None),
            limitations=())
    rec.run("SEC-10", "container image scan",
            lambda: (None, "not applicable: G01 uses Linux network namespaces, no container images",
                     None), limitations=())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="shield.g01_suite")
    parser.add_argument("mode", choices=["cycle", "static"])
    parser.add_argument("cycle", nargs="?", default="static")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    if os.geteuid() != 0 and args.mode == "cycle":
        print("the runtime cycle needs root (network namespaces)", file=sys.stderr)
        return 2
    name = f"cycle-{args.cycle}" if args.mode == "cycle" else "static"
    rec = Recorder(args.artifacts / name, args.run_id, name)
    print(f"G01 {name} ({rec.environment_id})", flush=True)
    if args.mode == "cycle":
        run_cycle(rec)
    else:
        run_static(rec)
    statuses = [json.loads(p.read_text())["status"] for p in rec.tests.glob("*.json")]
    print(f"  {statuses.count('PASS')} passed, {statuses.count('FAIL')} failed, "
          f"{statuses.count('SKIPPED')} skipped", flush=True)
    return 1 if "FAIL" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
