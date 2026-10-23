# CLEARGLASS LEGAL GUARDIAN

Legal-analysis, legal-operations and risk-monitoring agent for ClearGlass Inc.
and, under a separate personal mandate, Desmond Otieno Odhiambo.

| File | What it is |
|------|-----------|
| `system_prompt.md` | The agent's operating prompt (§1–§19) |
| `agent.json` | Manifest: scope, forbidden actions, escalation rules |
| `../../bots/legal_guardian_bot.py` | The control layer. Enforces §2, §3, §4, §5, §11, §13, §14, §15 and §19 in code |
| `../../data/legal-guardian/` | Live registers: monitoring, deployment gate, deadlines |
| `examples/` | Synthetic inputs for every gate. Not real obligations |
| `../../tests/test_legal_guardian_bot.py` | Governance tests. They fail if a gate stops gating |

Not legal advice. The agent is not a lawyer, and its output does not create
legal representation or privilege.

## What runs automatically, and what does not

The control layer runs in code with no model involved: every external action
goes through `gate_action()`, every source goes through `check_source()`, and
every matter goes through `check_matter()`. The model cannot talk its way past
these checks.

What a prompt cannot do on its own:

- **"Full authorization" is not approval.** §15 says "protect me", "handle it"
  or a general role assignment does not approve future external actions. The
  engine enforces this. An approval covers one exact action, through a SHA-256
  digest of its tool, target, content, attachments, disclosure scope and
  conditions. If any of those change, the action needs a new approval.
- **Monitoring is `NOT ACTIVE`.** No scheduler, connector or alert channel has
  been configured and evidenced in `data/legal-guardian/monitoring.json`.
  `--status` reports that honestly.
- **Unattended operation is `NOT APPROVED`.** The §19 gate needs 15 items of
  evidence, each verified by a named human with a date. Three have code
  evidence in this repo (approval enforcement, audit logging, injection
  tests). None has human verification yet.

## Commands

```bash
python -m bots.legal_guardian_bot --self-check          # 18 governance invariants
python -m bots.legal_guardian_bot --status              # monitoring + §19 gate + deadlines
python -m bots.legal_guardian_bot --deadlines data/legal-guardian/deadlines.json --strict
python -m bots.legal_guardian_bot --gate-matter  agents/clearglass_legal_guardian/examples/matter.example.json
python -m bots.legal_guardian_bot --gate-source  agents/clearglass_legal_guardian/examples/source.example.json
python -m bots.legal_guardian_bot --gate-action  agents/clearglass_legal_guardian/examples/action.example.json \
    --approvals approvals.json
python -m bots.legal_guardian_bot --screen email.txt    # §14 injection markers
python -m bots.legal_guardian_bot --verify-audit audit.jsonl
```

Every command takes `--json`. `--audit-log FILE` appends a hash-chained record
that holds only a digest of the input and the outcome, never the matter
content. With `--strict`, the command exits with code 2 on a P0 deadline or a
blocked gate, so a scheduler can alert on it.

## Approving one action

1. Write the action with every §15 field (see `examples/action.example.json`).
2. `python -m bots.legal_guardian_bot --digest action.json` prints its digest.
3. The authorized approver records the approval, with an expiry and
   `"used": false`:
   `{"approvals": [{"action_id": "...", "digest": "...", "approver": "...", "expires_at": "2026-11-01T00:00:00Z", "used": false}]}`
4. Run `--gate-action action.json --approvals approvals.json`. The result is
   `APPROVED FOR EXECUTION — RESULT NOT YET VERIFIED`. The action is complete
   only after its real outcome has been checked (§17). Mark the approval
   `"used": true` once it has executed, because each approval works only once.

Prohibited kinds stay blocked even with a matching approval. These include
location tracking, covert monitoring, access to personal accounts, deleting or
altering evidence, and disabling logging.

## Adding a deadline

Add it to `data/legal-guardian/deadlines.json`, with a documented source,
`trigger_date` and `calculation_rule` (`{"unit": "calendar_days" | "business_days", "count": N}`).
The engine never invents a trigger date or a rule. It shows the earliest
plausible date as `PROVISIONAL — DO NOT RELY WITHOUT VERIFICATION` until
`verified_date` and `verifier` are filled in. An unverified deadline within
14 days is P0. A deadline with no date that can be calculated is P1.

## Turning on unattended operation

For each gate in `data/legal-guardian/deployment.json`, fill in `evidence`,
`verified_by` and `verified_on`. When `--status` reports
`APPROVED FOR UNATTENDED OPERATION`, a scheduler can run
`--status --strict --json` and `--deadlines ... --strict`. Record its run
evidence in `monitoring.json` so that monitoring can be reported as active.
GitHub Actions in this repository dispatches no runners (see `CLAUDE.md`), so
the scheduler must run somewhere else.
