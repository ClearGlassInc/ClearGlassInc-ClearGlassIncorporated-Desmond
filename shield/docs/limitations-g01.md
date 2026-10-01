# ClearGlass Shield G01 Limitations

G01 demonstrates a controlled technical test harness, not a deployable service.

Validated scope is limited to an ephemeral Linux network-namespace topology using the standard WireGuard implementation and synthetic HTTP/DNS services. The data plane is the kernel WireGuard module where the host kernel has one, and otherwise wireguard-go, the WireGuard project's userspace implementation, from the Ubuntu archive. Each evidence file records which one ran.

```text
NETWORK LOCK VALIDATED ONLY FOR THE DEFINED LINUX/CONTAINERIZED
G01 TEST TOPOLOGY. THIS DOES NOT PROVE PROTECTION AGAINST ALL
PLATFORM-SPECIFIC, HOST-LEVEL, DNS, ROUTING, OR APPLICATION-LEVEL
LEAKAGE CONDITIONS.
```

The evidence does not establish:
- production readiness;
- independent audit or certification;
- universal leak prevention;
- no-logging/privacy guarantees;
- customer suitability;
- public gateway availability;
- cross-platform behavior (Windows, macOS, mobile, public networks);
- performance, load, DDoS, multi-region or availability objectives;
- billing, entitlement, subscription or account behavior.

Known gaps inside the G01 scope:
- An unknown, invalid or revoked peer receives no reply from a WireGuard gateway, by protocol design. The client cannot tell these apart, so all three surface as `HANDSHAKE_FAILURE`; the `REVOKED` and `AUTH_FAILURE` states exist but are not reached in G01.
- `GATEWAY_UNAVAILABLE` is inferred from the underlay: the gateway host does not answer a TCP connection attempt on the WireGuard port. A host that answers but runs no tunnel is a handshake failure.
- The configuration is validated, not signed. No signing claim is made.
- SEC-09 (dependency vulnerability audit) and SEC-10 (container image scan) are not run and are recorded as SKIPPED, never as PASS. `shield/` uses only the Python standard library, and G01 uses network namespaces rather than container images.
- Test telemetry is not production observability.

The words PASS/FAIL in G01 evidence refer only to the defined automated test criteria.
