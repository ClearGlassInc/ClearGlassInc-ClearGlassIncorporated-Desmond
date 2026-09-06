# ClearGlass Repo Audit Pack

A production-ready, dependency-free audit harness that discovers repositories
and scores each on **workflow health, dependency hygiene, and bot/automation
status** — making "patched / clean / actively executing" measurable per repo.

> Files: [`scripts/repo_audit.py`](../scripts/repo_audit.py) ·
> [`scripts/repo_audit.sh`](../scripts/repo_audit.sh) ·
> workflow [`.github/workflows/repo-audit.yml`](../.github/workflows/repo-audit.yml) ·
> tests [`tests/test_repo_audit.py`](../tests/test_repo_audit.py)

## Auth model (read this first)

The token is read from the **`GITHUB_TOKEN` environment variable only**. The
pack deliberately does **not** read `~/.github_token` and does **not** run
`gh auth login --with-token` — piping long-lived tokens through files/CLI login
is the easiest way to leak them. Use a short-lived, **read-scoped** token in
your shell or CI secrets instead. The audit performs **read-only** API calls and
never writes to any audited repository.

## Run it

```bash
# Self-audit of the current checkout — no network, no token
scripts/repo_audit.sh

# Whole org/user — discovery + per-repo audit (needs a read token in the env)
export GITHUB_TOKEN=...          # org-scoped, read-only
scripts/repo_audit.sh ClearGlassInc
```

Equivalent direct invocations:

```bash
python3 scripts/repo_audit.py --self                 # this repo
python3 scripts/repo_audit.py --org ClearGlassInc    # every repo in the org
python3 scripts/repo_audit.py --offline              # deterministic fixture (tests)
```

In CI, **Repo Audit** runs weekly (and on demand) and uploads the reports as a
build artifact. It holds only `contents: read`.

## What it measures

| Dimension | How |
|---|---|
| **Workflow health** | Latest-per-workflow conclusion over the last 50 runs → success rate, last success/failure timestamps, failing names, and run URLs as exact failure evidence |
| **Bot status** | `healthy` ≥90% · `degraded` ≥50% · `failing` <50% · `unverified` (workflows exist but no completed-run evidence) · `none` (no workflows) |
| **Operational status** | Evidence-safe vocabulary: `RUNNING_BUT_UNVERIFIED` for successful CI (which is not production proof), `CODE_FAILURE` for observed CI failures, or `DISABLED` when no workflows exist |
| **Python deps** | `requirements.txt` lines classified pinned (`==`/range) vs unpinned (bare name) |
| **Node deps** | `package.json` deps pinned to a moving target (`*` / `latest`) flagged |
| **Score / grade** | Composite 0–100 → A–F; penalizes red CI, missing workflows, missing completed-run evidence, and dependency drift |

## Outputs (`audit-reports/`)

- `repo_audit.csv` — one row per repo with every column above (drop into a sheet)
- `repo_audit.json` — the same rows plus a portfolio `summary`:
  repos audited, average score, repos with failing CI, repos with unpinned deps,
  and the A–F grade distribution

The audit deliberately never reports `LIVE_AND_VERIFIED`: a GitHub Actions run
cannot prove external health, payment completion, fulfillment, or production
deployment. Those claims require separate endpoint and processor evidence.

## Scope note

When run from a session whose GitHub access is restricted to a single repo, use
`--self`. The `--org` path fans out across the whole portfolio the moment it runs
with an org-scoped token (locally or in the **Repo Audit** workflow).

## Extending

`scripts/repo_audit.py` keeps all scoring in small **pure functions**
(`workflow_health`, `audit_python_deps`, `audit_node_deps`, `score_repo`,
`summarize`) so new signals (secret scanning, CODEOWNERS, branch protection) can
be added with a unit test alongside each. See `tests/test_repo_audit.py`.
