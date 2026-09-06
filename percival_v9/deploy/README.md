# Percival v9 — Deploy Layer (authored, NOT provisioned)

> **Nothing here is applied.** These are version-controlled infrastructure-as-code
> artifacts for review. Creating real infrastructure (`terraform apply`, `kubectl
> apply`) is an external, cost-incurring, irreversible action that requires cloud
> credentials **and** explicit human approval — the same Escalation Gate the
> Percival governor itself enforces. CI does not run any of this.

| Path | What it is | How it's checked here |
|------|-----------|-----------------------|
| `k8s/orchestrator.yaml` | Orchestrator Deployment + OPA governor **sidecar** | YAML well-formedness + structural test |
| `k8s/governor-configmap.yaml` | Policy bundle mounted read-only into the sidecar | Kept **in sync** with `policies/capabilities.json` (test-enforced) |
| `temporal/worker.py` | Durable workflow worker, governor-gated | Import-guarded: no-ops if `temporalio` absent, so CI stays green |
| `terraform/` | EKS + IAM + RDS skeleton | `terraform fmt/validate` are **manual** (no binary in CI) |
| `gateway/envoy.yaml` | Envoy API gateway: OIDC JWT auth, rate limit, `ext_authz`→governor (fail-closed) | YAML well-formedness + security-invariant test |
| `docker-compose.yml` + `Dockerfile.governor` | **Local, credential-free** run of governor + gateway | Compose structure test (no Docker in CI) |

## Run it locally (no cloud, no credentials)

```bash
cd percival_v9/deploy && docker compose up --build
```

Brings up the real stdlib Policy Governor behind Envoy so you can exercise the
`JWT → rate-limit → ext_authz(governor) → route` path and the fail-closed
behaviour on a laptop — the pre-provisioning validation step before any of the
gated cloud actions below.

## Provisioning path (each step gated on approval)

1. **Review** these files in a PR (done via normal review).
2. Operator supplies scoped cloud credentials via the environment's secret store
   (never pasted into chat or committed).
3. `terraform init && terraform plan` against a **non-prod** account — a plan,
   never a blind apply. Operator reads the plan.
4. Operator approves → `terraform apply`.
5. `kubectl apply -f k8s/` with images pinned to **digests** (not `:latest`).

## Hardening already baked in
- OPA sidecar and orchestrator images carry digest-pin TODOs, resource limits,
  and liveness/readiness probes (the source blueprint omitted these).
- `GITHUB_TOKEN`/IAM scopes are least-privilege.
- Policy bundle is mounted **read-only**; the governor fails closed on a stale
  bundle (see `internal/policy/engine.py` `stale-policy`).
