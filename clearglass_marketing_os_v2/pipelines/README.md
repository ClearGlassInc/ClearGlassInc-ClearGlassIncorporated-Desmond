# Marketing OS pipeline playbooks

These six files are **not GitHub Actions workflows**. They are declarative
pipeline definitions for the ClearGlass Marketing Operating System — the
governance layer described in `../agent.json` and `../system_prompt.md`.

Their schema is the marketing OS's own:

```yaml
name: outreach-approval
mode: fail-closed                 # dry-run | analysis-only | fail-closed
steps: [draft_message, verify_context, suppression_check,
        approve_exact_message, send_by_authorized_tool, log_outcome]
```

`mode` and the `human_approval_required` / `approve_exact_message` steps carry
the same read-only-by-default, approve-before-external-action invariant that
`agent.json` declares (`"mode": "dry_run_by_default"`,
`"approval_required_for_external_actions": true`,
`"default_authority": "READ_ONLY"`).

## Why they live here

The lossy web upload that flattened this repository swept them into the
top-level `workflows/` directory alongside the 72 real Actions workflows. They
have no `on:` trigger and no `jobs:` map, so registering them under
`.github/workflows/` would give GitHub six permanently invalid workflow files
and a red X on every push, forever — for files GitHub Actions was never meant
to read.

`scripts/audit_github_actions.py` is what caught them: it reported
`missing or empty trigger ('on')` and `missing or empty jobs map` for exactly
these six and for no other file in the archive.

## Adding a playbook

Keep the three keys above and nothing else. A playbook that needs to *run* in
CI needs a real workflow under `.github/workflows/` that invokes the engine
(`scripts/marketing_os_v2.py`, per `agent.json`'s `engine_path`); the playbook
itself stays declarative.
