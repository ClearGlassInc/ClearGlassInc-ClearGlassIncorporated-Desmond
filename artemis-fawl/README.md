# ARTEMIS // FAWL

Federated Autonomous Workflow & Intelligence Layer for ClearGlass Inc.

This additive module provides a GitHub Pages-compatible executive command surface plus a deterministic, permission-gated revenue-opportunity ranker. Existing pages, routes, scripts, metadata, and integrations are not replaced.

## Truth boundary

The interface is a static demonstration. Every visible business metric is labeled **SIMULATED**. It performs no authentication, scraping, trading, payment, outreach, deployment, or background execution. Production sources must be explicitly authorized and registered; absence of authorization fails closed.

## Revenue agent

`agents/artemis_fawl_revenue.py` ranks opportunities using fixed integer inputs and `Decimal` currency:

- evidence quality: 35%
- capped expected value: 25%
- strategic fit: 20%
- inverse effort: 10%
- inverse risk: 10%

It emits a deterministic SHA-256 audit hash. An authorized source is necessary but insufficient: external execution stays review-gated until a named human approval is recorded by a separate controlled executor.

## Run

```bash
python3 -m http.server 8000
# http://localhost:8000/artemis-fawl/
python -m pytest -q tests/test_artemis_fawl_revenue.py
```

## Production connection checklist

1. Authenticate on a backend; never place credentials in this directory.
2. Register source owner, authorization, classification, freshness, schema and retention.
3. Validate payloads, conflicts and timestamps.
4. Separate recommendation from execution.
5. Require identity-bound approval for high-impact actions.
6. Record evidence, policy, approver, outcome and rollback reference.
7. Replace demo values only after live-source tests pass.

## Rollback

Remove the additive `artemis-fawl/` directory, `agents/artemis_fawl_revenue.py`, its focused test, and the dedicated validation workflow. No existing page depends on these files.
