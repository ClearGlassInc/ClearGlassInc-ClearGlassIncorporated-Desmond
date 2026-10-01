# ClearGlass Shield G01 Threat Model

## Scope
Disposable Linux network-namespace test environment only. No production, customer, public, billing, or arbitrary internet traffic.

## Assets
- Disposable client private key
- Disposable gateway private key
- Synthetic test configuration
- Internal test DNS (`service.shield.test`, `health.shield.test`, `blocked.shield.test`)
- Internal test network (namespaces, veth on 192.0.2.0/30, tunnel on 10.77.0.0/24)
- Test evidence artifacts
- CI artifacts
- Source code and build dependencies (wireguard-tools, iproute2, iptables, wireguard-go)

## Trust boundaries
1. Test client namespace (`cgshield-client`)
2. Internal encrypted tunnel (WireGuard, `cgwg-c` to `cgwg-g`)
3. Test gateway namespace (`cgshield-gateway`)
4. Internal synthetic service (HTTP on 10.77.0.1:8080), the controlled egress target
5. Test DNS resolver (10.77.0.1:5353)
6. CI runner, or the local host running `run-g01.sh`
7. Artifact store (`artifacts/shield-g01/`, and `provenance/shield/runs/` once committed)

## In-scope threats

| Threat | Asset affected | Control | Test ID | Evidence artifact | Residual risk |
|---|---|---|---|---|---|
| Exposed private key | Client and gateway keys | `wg genkey` per environment, 0600 files in a 0700 directory outside the repo, deleted on teardown; only fingerprints exported | KEY-01, SEC-02 | `cycle-N/tests/KEY-01.json`, `SEC-02.json` | Root on the test host can read keys while the environment exists |
| Committed test secret | Source code | Secret scanner over `shield/`; `*.key` and `.env` git-ignored | SEC-01, SEC-03, FI-12 | `static/tests/SEC-01.json`, `SEC-03.json`, `FI-12.json` | Scanner is pattern-based; novel secret shapes can pass |
| Unauthorized gateway peer | Test network | Explicit WireGuard peer allowlist | FI-02 | `cycle-N/tests/FI-02.json` | None in scope |
| Invalid or revoked client identity | Test network | Peer removal on the gateway | FI-03 | `cycle-N/tests/FI-03.json` | Client cannot distinguish revocation from other handshake failures |
| Malformed configuration | Client | Strict validation: environment, endpoint range, CIDR, key shape, version, lock, DNS policy, no extra fields | FI-04, DNS-04, UNIT-01 | `cycle-N/tests/FI-04.json` | Configuration is validated, not signed |
| Insecure default configuration | Client and gateway | Network lock required (`network_lock: true`); services bind to the tunnel address only | FI-04 (CFG-07), BOOT-01 | `cycle-N/detail/BOOT-01.json` | None in scope |
| Invalid gateway configuration | Gateway | Gateway removes its tunnel when `wg` rejects a setting | FI-05 | `cycle-N/tests/FI-05.json` | Only key rejection is exercised |
| Tunnel failure | Test traffic | Lifecycle health check; lock stays active | FI-06, FI-01 | `cycle-N/tests/FI-06.json` | Detection is by probe, not continuous |
| Test DNS bypass | Test DNS | DNS allowed only through the tunnel interface | DNS-03 (with control) | `cycle-N/tests/DNS-03.json` | IPv6 is not exercised; namespaces have no IPv6 addresses |
| Protected-route leakage | Test traffic | Client-side lock: tunnel range only via the tunnel interface | LOCK-CTRL, LOCK-01..05 | `cycle-N/tests/LOCK-*.json` | Linux namespace topology only (see limitations) |
| Gateway restart failure | Availability in test | Restart with the same key and allowlist; client reconnects only after recovery | FI-08, DNS-05 | `cycle-N/tests/FI-08.json` | Single gateway, no HA |
| Client restart failure | Availability in test | Fresh tunnel on every connect | FI-09 | `cycle-N/tests/FI-09.json` | None in scope |
| Artifact tampering | Evidence | SHA-256 of every artifact in the evidence file | Evidence generator | `g01-runtime-evidence.json` `artifact_hashes` | Hashes are not signed |
| Unexpected outbound connection | Host network | No default route in either namespace; gateway does not forward | FI-11, SEC-04 | `cycle-N/tests/FI-11.json` | Root namespace is not instrumented |
| Debug endpoint exposure | Gateway | Only `/health` answers; services bound to 10.77.0.1 | FI-13, GW-01 | `cycle-N/tests/FI-13.json` | None in scope |
| Unsafe log or telemetry content | Evidence | Closed telemetry field allowlist; exact-key leak scan; artifact secret scan | SEC-07, SEC-02, SEC-06 | `cycle-N/tests/SEC-07.json` | Free-text fields are length-capped, not semantically checked |
| Teardown failure | Host | Destroy plus independent verify-clean | FI-14 | `cycle-N/tests/FI-14.json`, `cycle-N/verify-clean.json` | None in scope |

## Explicit G01 limitations
- No independent security audit.
- No production-network validation.
- No mobile, Windows, macOS, or public-network validation.
- No claim that network lock prevents all traffic leaks.
- No claim that test telemetry equals production observability.
- No customer privacy claim.
- No "no logs" claim.
- No billing, entitlement, subscription, or user-account testing.
- No load, DDoS, geographic, multi-region, or high-availability testing.
- No public DNS, public ingress, customer identity, or production secret validation.

## Residual risk
Platform-specific routing, DNS, host firewall, application behavior, kernel, container runtime, and operational controls remain outside the G01 proof boundary.
