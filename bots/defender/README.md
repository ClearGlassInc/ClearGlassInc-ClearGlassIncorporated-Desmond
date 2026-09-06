# ClearGlass Defender

A defensive security orchestrator for this repository. It assumes compromise is
possible and works to **see it early and limit blast radius** — a practical
zero-trust posture for the CI/CD and supply-chain surface.

It is built as three layers:

| Layer | Module | Responsibility |
| --- | --- | --- |
| **Sensor** | `engine.py` | Scan workflows, secrets, dependencies, and the command surface; emit structured findings. |
| **Policy** | `policy.py` + `bots/config/defender_policy.json` | Classify findings by severity, apply allowlists, and decide the graded response — all from one JSON policy. |
| **Response** | `alerting.py`, `quarantine.py` | Alert the right channels and write an **advisory, non-destructive** quarantine record. |

## What it checks

- **Workflow integrity** — actions pinned to a full commit SHA (not tags or
  `@latest`), an explicit least-privilege `permissions:` block, no
  `pull_request_target` surprises, and no untrusted `${{ github.event.* }}`
  interpolation inside `run:` steps (script injection).
- **Secret exposure** — high-confidence credential formats (AWS keys, GitHub /
  GitLab / Slack tokens, private-key blocks) plus conservative generic
  assignments. Evidence for any suspected secret is **redacted** before it is
  written anywhere.
- **Dependency hygiene** — unpinned Python requirements (the workflow runs the
  real `pip-audit` / `npm audit`).
- **Suspicious commands** — `curl … | bash`, encoded PowerShell, reverse shells,
  `rm -rf /`, disk wipes — scoped to the automation surface.
- **Correlation** — combines related findings into higher-severity incidents
  (e.g. *secret exposure + workflow change* → likely exfiltration setup).

## Non-destructive by design

Quarantine here means **flag-for-review, not delete**. The engine never modifies,
deletes, disables, or rewrites repository content. It records a tamper-evident
incident (with per-file SHA-256) and the recommended response actions; the *real*
enforcement is branch protection, required reviews, and token rotation — owned by
humans acting on the record.

## Running it

```bash
# Full scan + response; writes to operations/output/defender/
python -m bots.defender

# Via the universal bot runner
python scripts/bot_runner.py defender
```

The CLI exits non-zero only when a finding's severity is in
`enforcement.fail_build_on` (default: `critical`), so routine hygiene findings
(`high`) surface as warnings/artifacts without breaking the build.

## Outputs (`operations/output/defender/`)

| File | Contents |
| --- | --- |
| `defender_report.json` / `.md` | Full findings, severity summary, response plan. |
| `alerts.json` | Which channels fired (GitHub Issue / Slack / Discord). |
| `quarantine.json` / `.md` | Advisory containment record with per-file SHA-256. |

## Configuration

Everything tunable lives in [`bots/config/defender_policy.json`](../config/defender_policy.json):
patterns, severities, allowlists, build gate, and the graded response plan. The
engine reads the policy and hard-codes no rules.

Optional alert channels (all off unless the secret is set), wired in
`.github/workflows/defender-watch.yml`:

- `GITHUB_TOKEN` — opens an incident issue for **critical** findings only.
- `DEFENDER_SLACK_WEBHOOK_URL` — Slack incoming-webhook summary.
- `DEFENDER_DISCORD_WEBHOOK_URL` — Discord webhook summary.

## Tests

```bash
python -m pytest tests/test_defender_*.py -q
```
