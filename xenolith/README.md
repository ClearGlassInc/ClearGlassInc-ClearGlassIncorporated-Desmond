# XENOLITH — Sovereign Intelligence Lattice

A governed, multi-domain command substrate. Executive orchestration,
intelligence fusion, cyber defense, threat intelligence, telemetry and
autonomous agents run as independent subsystems over one shared identity layer,
one event bus, one memory fabric and one policy gate.

**Stdlib only.** No third-party packages, no services, no network. The
governance gate runs unchanged in a minimal CI container.

## The invariant

```
sign → verify → capability → risk gate → (human approval) → execute → audit
```

`Lattice.submit` is the only way in. There is deliberately no method that skips
the gate. An action scoring `high` or `critical` returns `executed=False` with
an approval id, and nothing runs until `Lattice.approve` records a decision from
someone who is **not** the requester.

## Quick start

```bash
python -m xenolith.cli --check     # governance invariants; exits 1 on failure
python -m xenolith.cli             # human-readable status report
python -m xenolith.cli --json      # full lattice state as JSON
python -m xenolith.cli --write     # regenerate data/xenolith/lattice.json
python -m pytest tests/test_xenolith_*.py -q
```

```python
from xenolith import Lattice, Domain

lat = Lattice()
lat.enlist(
    "BASTION", Domain.CYBERSECURITY,
    role="containment", mission_scope="respond to intrusions",
    sponsor="ops", permissions=["cyber.respond"],
)

out = lat.submit("BASTION", "cyber.contain", {"asset": "edge-gateway-01"})
out.executed              # False — containment is irreversible, scored 84
out.verdict.tier.value    # 'high'

lat.approve(out.approval_id, "human-operator")   # self-approval raises
lat.submit("BASTION", "cyber.contain", {"asset": "edge-gateway-01"}).executed  # True
```

## Modules

| Module | Responsibility |
|--------|----------------|
| `constants` | Shared vocabulary: `Domain`, `RiskTier`, error family, canonical serializer |
| `identity` | HMAC-derived agent keys, signed single-use envelopes, replay protection, revocation |
| `registry` | Codename, domain, role, mission scope, permissions, memory partition, status, health, heartbeat |
| `bus` | Typed events, total ordering, exactly-once acceptance, handler isolation, replay |
| `policy` | Deny-by-default gate, 0–100 risk scoring, digest-bound approvals, output sanitization |
| `memory` | Partitioned fabric; writes subtree-confined, cross-partition reads need a grant |
| `graph` | Entities, relationships, provenance, confidence, contradiction tracking |
| `telemetry` | Hash-chained audit ledger, counters/gauges, model-free anomaly detection |
| `fusion` | Connectors → observations → clusters → corroborated intelligence packets |
| `executive` | Objectives → policy-constrained missions → priority-ranked tasks |
| `lattice` | The composed platform and the single governed entry point |
| `constellation` | The synthetic reference deployment CI and the command surface use |
| `cli` | Self-check and operator feed generation |

## Design decisions worth knowing

**Risk tiers match the commerce control plane.** `RiskTier.from_score`
boundaries mirror `clearglass-commerce/control-plane/app/governance.py`, so a
risk score means the same thing across the ClearGlass estate.

**Approvals bind to a content digest.** Approving one containment does not
approve the next; mutating a payload after approval invalidates it.

**Delegation cannot escalate.** A sub-agent's permissions are intersected with
its parent's and its memory partition nests beneath the parent's, so recursive
spawning stays inside the original grant.

**Contradictions are recorded, not resolved.** Two sources disagreeing on a
single-valued attribute both survive and the pair is surfaced. Multi-valued
predicates (`observed_by`) are exempt — several sources naming themselves is
corroboration.

**Failures are isolated, not fatal.** A raising bus handler becomes a dead
letter; a broken connector is recorded and skipped; a failing executor is
audited with its error rather than propagating out of `submit`.

**The root secret is generated per process.** Agent keys are HMAC-derived on
demand, so no key material is written to disk or committed. Inject a root secret
from the environment only when identities must survive a restart.

## What this is not

The reference constellation in `constellation.py` is synthetic and offline —
fixed feeds, no credentials, no network calls. It exists so the governance gate
has something real to exercise and the command surface at `/xenolith.html` has
something honest to render. Wiring real connectors means implementing
`fusion.Connector.fetch` against a real source and grading its reliability.
