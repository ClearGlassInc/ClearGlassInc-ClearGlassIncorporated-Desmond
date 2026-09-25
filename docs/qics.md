# QICS v2.0 — Quantum Intelligence Command System

Evidence-first cryptographic-readiness layer. It is **not** a quantum computer,
**not** a compliance certification, and **not** wired into production checkout.

## What it does

```
python -m qics --tenant demo --inventory inventory.json
```

Input is a declared algorithm inventory. Output is a rating, investigation-only
recommendations, opportunities without guaranteed revenue, bundled NIST/CISA
references, and an append-only in-process audit event.

Ratings: `LOW_EXPOSURE` | `MODERATE_EXPOSURE` | `HIGH_EXPOSURE` |
`CRITICAL_EXPOSURE` | `INSUFFICIENT_DATA`.

`LOW_EXPOSURE` is not “quantum safe.”

## What it does not do

- Live NIST/CISA HTTP ingestion (connectors return `SOURCE_UNAVAILABLE`)
- Change TLS, certificates, or production controls
- Speak for a deployed control-plane (that service is still undeployed)
- Appear on https://www.clearglassinc.com/ navigation
- Count pipeline or hypotheses as verified intelligence

## Reuse

When the control plane is deployed, route material QICS recommendations through
existing `/approvals` and `log_event`. This package does not duplicate those
tables.

## Tests

```
cd repo-root && python -m pytest tests/test_qics.py -q
```
