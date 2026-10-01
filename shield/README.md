# ClearGlass Shield — Isolated Disposable MVP

Disposable, non-production G01 test harness. It is not a VPN service and must not be used for customer traffic.

Boundary: no Stripe integration, no production gateways, no public listener, ephemeral test credentials, deterministic teardown.

| Path | Role |
|---|---|
| `client/config.py` | Configuration validation (test environment, endpoint range, CIDR, key shape, DNS policy, network lock) |
| `client/controller.py` | Client lifecycle state machine; runs inside the client namespace |
| `client/telemetry.py` | Test-only telemetry with a closed field allowlist |
| `gateway/health.py` | Gateway health endpoint, tunnel address only |
| `topology.py` | Build, operate and destroy the namespaces, tunnel, lock and services |
| `g01_suite.py` | The G01 tests; one JSON record per test |
| `evidence.py` | Maps records onto the acceptance criteria and computes the gate |
| `secret_scan.py` | Secret scanner for `shield/` and evidence artifacts |
| `docs/` | Threat model, limitations, operations |

G01 status is whatever `evidence.py` computes from a recorded run: PASS only when every mandatory criterion passes in both cycles and teardown completes. There is no override. See `docs/operations-g01.md` to run it.
