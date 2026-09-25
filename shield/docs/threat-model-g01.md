# ClearGlass Shield G01 Threat Model

## Scope
Disposable Linux network-namespace test environment only. No production, customer, public, billing, or arbitrary internet traffic.

## Assets
- Ephemeral WireGuard client/gateway private keys
- Synthetic configuration and DNS records
- Test network namespaces and routes
- Non-sensitive test evidence
- CI artifacts
- Source code and dependencies

## Trust boundaries
1. Test client namespace
2. WireGuard tunnel
3. Test gateway namespace
4. Internal synthetic HTTP/DNS services
5. GitHub Actions runner
6. Non-sensitive artifact output

## In-scope threats

| Threat | Control | Test |
|---|---|---|
| Private key exposure | Ephemeral files, 0700/0600 permissions, secret scan | SEC-01 |
| Unauthorized peer | Explicit WireGuard peer allowlist | FI-02/FI-03 |
| Invalid configuration | Strict schema/environment/CIDR validation | CFG-01..05 |
| Tunnel failure | Lifecycle state and connectivity probes | FI-01/FI-06 |
| DNS bypass | Internal synthetic resolver and policy test | DNS-01..05 |
| Protected-route leakage in test scope | Test-only network lock policy | LOCK-01..05 |
| Unexpected egress | No public route and explicit network policy | SEC-04 |
| Debug exposure | Health endpoint restricted to test namespace | SEC-05 |
| Artifact leakage | Evidence allowlist and secret scan | SEC-01/SEC-06 |
| Teardown failure | Destructive cleanup plus verify-clean | FI-14 |

## Explicit G01 limitations
- No independent security audit.
- No production-network validation.
- Linux/container test scope only.
- No mobile, Windows, macOS, public-network, multi-region, HA, load, or DDoS validation.
- No universal kill-switch/leak-proof claim.
- No customer privacy or no-logs claim.
- No billing, entitlement, subscription, or account testing.
- No public DNS or public ingress.
- Test telemetry is not production observability.

## Residual risk
Platform-specific routing, DNS, host firewall, application behavior, kernel, container runtime, and operational controls remain outside the G01 proof boundary.
