# ClearGlass Platform (`/platform`)

The Internal Developer Platform layer: governance, policy, supply-chain, and
golden paths as code. The goal is **safety as the path of least resistance** —
the easy way to ship is automatically the secure, compliant, observable way.

## Layout

| Path | Purpose |
|---|---|
| `policies/workflow/` | OPA/Rego policy for GitHub Actions (`deny` blocks, `warn` advises) + unit tests |
| `policies/terraform/` | IaC guardrails evaluated by Conftest |
| `policies/k8s/` | Kyverno admission control — rejects unsigned/unattested images |
| `delivery/` | Argo Rollouts canary with SLO-gated auto-rollback |
| `actions/` | Reusable composite actions (golden-path CI) |
| `catalog/` | Backstage service catalog entries |

Companion: `infra/github/` holds GitHub-as-code (rulesets) and
`.github/workflows/policy-gate.yml`, `release-supply-chain.yml`, and
`compliance-evidence.yml` wire the platform into CI.

## Policy severities & promotion path

The policy bundle (`policies/workflow/actions.rego`) intentionally ships
SHA-pinning as **`warn`** so it does not break the existing fleet, which still
uses tag refs (e.g. `actions/checkout@v5`). Genuinely dangerous patterns
(`write-all`, missing `permissions`, pwn-request checkout) are hard **`deny`**.

**To promote SHA-pinning to a hard gate:**

1. Pin every `uses:` in `.github/workflows/*.yml` to a 40-char commit SHA
   (Dependabot keeps them fresh — see `.github/dependabot.yml`).
2. In `actions.rego`, move the `warn contains msg if { ... is_sha_pinned ... }`
   rule to `deny contains msg if { ... }`.
3. `conftest verify --policy platform/policies` must stay green (tests in
   `actions_test.rego` cover both severities).

## Run policies locally

```bash
# Install conftest, then:
conftest verify --policy platform/policies          # unit-test the policies
conftest test .github/workflows/*.yml infra/github/*.tf --policy platform/policies
```

## Make the gate enforcing

Add **"Policy Gate"** to the required status checks in
`infra/github/variables.tf` (already listed) and apply
`infra/github/rulesets.tf`.
