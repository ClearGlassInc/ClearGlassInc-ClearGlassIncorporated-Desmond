# Cross-Repo GitHub Actions — Patterns & Prompt Pack

> Reference + prompt pack for designing secure, modular cross-repository
> automation at ClearGlassInc. Covers when to use `workflow_call` vs
> `repository_dispatch` vs scheduled polling, with least-privilege token and
> permission boundaries. **This doc adds no live cross-repo triggers** — wiring a
> real dispatch needs a PAT secret and touches `.github/workflows/`, an
> approval-worthy change.

---

## Decision rules

| Pattern | Use when | Trigger | Secrets |
|---|---|---|---|
| **`workflow_call`** (reusable) | Repos are tightly coupled, you control both, want shared reusable logic with typed inputs | Caller `uses:` the reusable workflow | Passed explicitly via `secrets:` or `secrets: inherit` |
| **`repository_dispatch`** | Repos are loosely coupled; one repo triggers another asynchronously with a custom payload | `POST /repos/{owner}/{repo}/dispatches` | **PAT** with `repo`/`actions` scope on the target |
| **Scheduled polling** | GitHub can't natively observe the source and no event trigger exists | `on: schedule` (cron) | Only what the poll needs |

Rule of thumb: **`workflow_call` for shared internal logic, `repository_dispatch`
for event-driven coordination between repos.**

---

## Required behavior when generating a cross-repo workflow

1. Identify the **source** repo and the **target** repo.
2. Choose the correct trigger mechanism (table above).
3. Define the **payload/inputs** — pass only the minimum necessary data.
4. Enforce **least-privilege** `permissions:` (default to `contents: read`, add only what's needed).
5. Use secrets safely — never echo them; never `run: echo ${{ secrets.X }}`.
6. **Log every cross-repo handoff** — treat it as a trust-boundary crossing.
7. Keep workflows modular and debuggable (one responsibility each).

---

## Security rules (non-negotiable)

- **Token scope:** the built-in `GITHUB_TOKEN` can only dispatch **within the same
  repo**. Cross-repo `repository_dispatch` requires a **PAT** (fine-grained,
  scoped to the target repo's Actions/Contents) stored as a secret.
- **Prefer `workflow_call`** when you control both repos — it centralizes logic and
  removes a cross-repo credential entirely.
- **Pin third-party actions to a commit SHA**, not a moving tag, on any workflow
  that crosses a trust boundary.
- Never expose secrets in logs; never assume access to another repo without
  explicit permission; **never trigger production actions without an approval
  gate** (GitHub Environments with required reviewers).

---

## Output contract (what the AI should return)

- A short **recommendation** of the best pattern and *why*.
- The **sender** workflow.
- The **receiver** workflow.
- **Required secrets** and **required permissions**.
- For a chain, the full flow, e.g. `Repo A builds → Repo B tests → Repo C deploys`.

---

## Standard templates

### `repository_dispatch` — sender

```yaml
name: Trigger Repo B
on:
  push:
    branches: [main]

permissions:
  contents: read           # least privilege; PAT carries the cross-repo scope

jobs:
  trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Send dispatch to Repo B
        env:
          PAT_TOKEN: ${{ secrets.PAT_TOKEN }}   # fine-grained PAT, target-repo scoped
        run: |
          curl -sfL -X POST \
            -H "Authorization: Bearer $PAT_TOKEN" \
            -H "Accept: application/vnd.github+json" \
            https://api.github.com/repos/OWNER/REPO_B/dispatches \
            -d '{"event_type":"run-workflow","client_payload":{"version":"1.2.3"}}'
          echo "Dispatched run-workflow → OWNER/REPO_B (version 1.2.3)"   # handoff log
```

### `repository_dispatch` — receiver

```yaml
name: Run on dispatch
on:
  repository_dispatch:
    types: [run-workflow]

permissions:
  contents: read

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Triggered from ${{ github.event.client_payload.version }}"
```

### Reusable workflow (`workflow_call`) — receiver

```yaml
name: Reusable build
on:
  workflow_call:
    inputs:
      version: { required: true, type: string }
    secrets:
      DEPLOY_KEY: { required: false }

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Building version ${{ inputs.version }}"
```

### Caller workflow

```yaml
jobs:
  call:
    uses: OWNER/REPO_B/.github/workflows/build.yml@<commit-sha>
    with:
      version: "1.2.3"
    secrets: inherit
```

---

## Operational guidance

- Pass only the minimum payload between repos; treat every cross-repo trigger as
  a reviewed, logged trust-boundary crossing.
- Gate anything that reaches production behind a GitHub **Environment** with
  required reviewers — the same approval-before-execution principle used across
  this repo's governance model.
- This repo already runs ~29 workflows and a **Workflow Doctor** gate; validate
  any new workflow with `python scripts/workflow_doctor.py` before it lands.
