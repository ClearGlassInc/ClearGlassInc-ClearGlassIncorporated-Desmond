# APEX Intelligence Core — existing-system integration

**Status: initial plan-only integration.** This is working control-plane code, not a claim that a multi-agent mesh, quantum computer, NSA/DARPA capability, or continuous autonomous runtime has been provisioned.

## Runtime entry point

- **POST /apex/plan** is added to the existing FastAPI control plane.
- The route is administrative: it requires the existing require_admin control-plane dependency and uses the existing decision-rate limiter.
- It scores the proposed action through control-plane/app/governance.py::score_action, whose unknown-action behavior fails closed.
- Every successful plan request writes a metadata-only event through the existing append-only audit writer. The objective itself and source URIs are not written to that event; the objective fingerprint is keyed with CRCS_AUDIT_HASH_KEY.
- It returns an explicitly planned_only envelope. It has no execution adapter, external tool, model call, source fetching, deployment, outbound messaging, payment or calendar mutation.

Example request (requires the control plane's configured admin bearer credential):

    POST /apex/plan
    {
      "mission_id": "SECURITY-REVIEW-01",
      "objective": "Review the defensive architecture and list evidence gaps.",
      "requested_action": "deploy_high_risk_change",
      "sources": [
        {
          "source_id": "ARCH-01",
          "uri": "repo://docs/security.md",
          "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        }
      ]
    }

The response carries the existing governance score and approval verdict for the proposed action, the specialist work plan, provenance status, a keyed plan fingerprint, and execution_status: not_executed. A declared SHA-256 is not proof that APEX read or validated the file bytes; it is labeled declared_not_verified. No URI is fetched.

## Roles wired into the plan

- **Cortex:** decomposes the objective into acceptance criteria and explicit assumptions.
- **ARTEMIS:** creates a source-indexed evidence map, retains contradictions, and labels missing data as unknown.
- **AEGIS:** applies the existing risk policy and highlights human-approval boundaries.
- **Sentinel:** supplies an independent critique and residual-risk list.
- **Quantum Research:** included only when the objective asks for quantum, optimization or scheduling work; it drafts a benchmark protocol and submits no job.

These are planned work packets, not claims that independent live agents ran. Existing names and product taxonomy are preserved; APEX is an internal integration module, not a new registered ClearGlass platform/product.

## Quantum benchmarking discipline

compare_benchmarks accepts externally measured summary records and checks that the problem and constraints fingerprints match. It distinguishes incomparable experiments, insufficient repetitions and candidate improvements that require independent review. It **never asserts quantum advantage**. The preliminary 30-sample floor is only a screening guard, not a statistical significance test or a substitute for distributions, repeated trials, cost/energy accounting, reproducibility and independent review. For the generic helper, lower objective value is treated as better; real experiments must state and justify their actual objective metric.

No QPU, quantum simulator, cloud account, SDK or quantum credentials are configured here. Benchmark execution is intentionally separate.

## Post-quantum security follow-through

Use a cryptographic inventory and staged crypto-agility assessment before changing cryptographic implementations. Align candidate migration planning to current NIST publications and review their current errata:
- [FIPS 203 — ML-KEM](https://csrc.nist.gov/pubs/fips/203/final)
- [FIPS 204 — ML-DSA](https://csrc.nist.gov/pubs/fips/204/final)
- [FIPS 205 — SLH-DSA](https://csrc.nist.gov/pubs/fips/205/final)

This PR does not change cryptographic algorithms, keys, certificates or TLS configuration.

## Verification and activation boundary

The tests in tests/test_apex.py cover the plan-only contract, risk fail-closed behavior, source-reference validation, quantum claim discipline and the current policy kernel. The existing control-plane route-auth test should also verify that /apex/plan rejects requests without admin credentials. GitHub Actions has previously failed to dispatch runners for this repository; report live Actions status separately from local or source-level checks.

Nothing in this integration promotes an action, changes production state, enables a model, executes a quantum workload, or assumes quantum advantage.
