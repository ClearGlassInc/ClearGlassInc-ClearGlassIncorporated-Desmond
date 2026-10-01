# G01 Operations

Requires root (network namespaces), Python 3.11+, `iproute2`, `wireguard-tools`, `iptables`, and either a kernel with WireGuard or `wireguard-go`. Run from the repository root.

| Step | Command | What it does |
|---|---|---|
| bootstrap shield g01 | `sudo bash shield/scripts/bootstrap-test-env.sh` | Builds the two namespaces, keys, gateway tunnel, network lock and services. Prints key fingerprints only |
| test shield g01 | `sudo bash shield/scripts/run-g01.sh` | Static checks, then two clean bootstrap, test, teardown and verify-clean cycles. Non-zero exit if anything failed |
| evidence shield g01 | `python3 shield/scripts/generate-evidence.py` | Computes the G01 gate from the run's records and writes `artifacts/shield-g01/g01-runtime-evidence.json` and its report. `--provenance` also writes the committed evidence and updates G01 in the release manifest |
| destroy shield g01 | `sudo bash shield/scripts/destroy-test-env.sh` | Stops processes, deletes namespaces and links, removes keys and state |
| verify-clean shield g01 | `sudo bash shield/scripts/verify-clean.sh` | Non-zero exit if any namespace, link, socket, process or key remains |

Environment identifier: `shield-g01-<short-commit>-<run-id>`. A local run's id is `local-<UTC timestamp>`; in CI it is the Actions run id.

Set `SHIELD_WG_BACKEND=kernel` or `userspace` to force a WireGuard implementation; the default picks the kernel module when present.

Rollback: revert the change and run `sudo bash shield/scripts/destroy-test-env.sh`, then `verify-clean.sh`.

No command in this directory may contact Stripe, production infrastructure, customer systems, or arbitrary public services. The namespaces have no default route, so they cannot.
