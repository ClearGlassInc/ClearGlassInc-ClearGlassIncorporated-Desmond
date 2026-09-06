# RFED™ Deployment

n8n workflow export, ledger schema, and runbook for the ClearGlass RFED™
audit-trail module. Pair with the spec at `docs/rfed_audit_trail_spec.md` and the
logic core at `bots/rfed_audit_bot.py`.

**RFED = Recorded Factual Evidence of Decision.** Every model-influenced action
is recorded as Request → Facts → Evidence → Decision, sealed into a SHA-256 hash
chain. That chain is the evidence of model accountability: it proves which model
saw which facts, what it produced, how it was scored, and who approved it.

## Files

| File | What it is |
|------|-----------|
| `workflow_rfed_audit_trail.json` | n8n workflow — signed ingress → grounded model call → governor → ledger → route |
| `audit_log.sql` | Append-only, chain-guarded Postgres/Supabase schema + operator views |
| `env.example` | Required credentials and instance settings |

## Deploy order

1. **Provision the ledger.** Run `audit_log.sql` against the client's Postgres.
   Create a `rfed_writer` role with `INSERT`/`SELECT` only — no `UPDATE`, no
   `DELETE`. The append-only trigger is the backstop; the missing grant is the
   actual control.
2. **Seed grounding sources.** Insert the allow-listed rows into
   `rfed_fact_sources`. The model can only ever be told what lives here. Mark
   anything internet- or user-supplied `trusted = false`.
3. **Provision n8n** (self-hosted Docker). Set `NODE_FUNCTION_ALLOW_BUILTIN=crypto`
   and `N8N_CONCURRENCY_PRODUCTION_LIMIT=1` — see the note on concurrency below.
4. **Create credentials**: Postgres (`RFED_PG_CRED_ID`), Anthropic API key, Slack
   webhooks. Import the workflow and map the placeholder credential IDs.
5. **Generate the ingress secret**: `openssl rand -hex 32` → `RFED_WEBHOOK_SECRET`.
   Give it to the calling agent; it signs `{timestamp}.{raw_body}`.
6. **Run in dry-run for 72 hours** (`RFED_DRY_RUN=true`, the default). Auto-routed
   actions call the executor with `dry_run: true`; nothing changes on the client
   estate. Review the drafted decisions in `rfed_pending_approvals`.
7. **Go live** only after the owner signs off on the dry-run ledger. Verify the
   chain first:
   ```bash
   psql -At -c "select ... from rfed_records order by occurred_at" > ledger.jsonl
   python -m bots.rfed_audit_bot --verify ledger.jsonl
   python -m bots.rfed_audit_bot --summary ledger.jsonl
   ```

## Calling the workflow

```bash
BODY='{"workflow":"client_zero_trust","action":"read_telemetry","target":"endpoint/BRL-014","intent":"check RMM agent patch level"}'
TS=$(date +%s)
SIG=$(printf '%s.%s' "$TS" "$BODY" | openssl dgst -sha256 -hmac "$RFED_WEBHOOK_SECRET" -hex | awk '{print $2}')

curl -sS -X POST https://n8n.example/webhook/rfed/propose \
  -H "content-type: application/json" \
  -H "x-clearglass-timestamp: $TS" \
  -H "x-clearglass-signature: $SIG" \
  -d "$BODY"
```

The response is a receipt: `record_id`, `chain_hash`, `route`, `tier`, `score`,
and the reasons. The caller can verify the decision independently — it never has
to trust the workflow's word for it.

## Risk controls baked into the workflow

- **Signed ingress.** HMAC-SHA256 over the raw body, constant-time compared, with
  a 300-second replay window. An unsigned or stale proposal never reaches the model.
- **Governed grounding.** Facts come only from `rfed_fact_sources`. Untrusted
  sources are scanned for prompt-injection markers; a hit gates the action.
- **Ledger-before-execute.** The record is durable *before* the action runs, so a
  crash mid-run leaves evidence rather than an untracked side effect.
- **Fail-closed routing.** Unknown actions score 85 (HIGH). The Switch node's
  fallback output is wired to the blocked branch, so an unroutable decision is
  treated as blocked, never as executable.
- **Never-automate set.** `modify_audit_log` is blocked outright, approved or not.
- **Ungrounded output is gated** even at low base risk — if the model cited
  nothing, there is nothing to audit against.
- **Dry-run by default.** `RFED_DRY_RUN` must be the literal string `false` to
  take effect.

## Concurrency

Ledger appends are serialised by design. The `rfed_records_chain_guard` trigger
rejects any insert whose `prev_hash` is not the current head, so two concurrent
runs cannot fork the chain — the loser fails loudly and retries. Keep
`N8N_CONCURRENCY_PRODUCTION_LIMIT=1` for this workflow; raising it converts a
correctness guarantee into a stream of retryable errors.

## Approvals

Approval is captured by a companion workflow that verifies the Slack signing
secret and **appends a new ledger row** (`bots/rfed_audit_bot.py::approve`). The
original record is never updated — the ledger is evidence, and evidence does not
change. `rfed_approvals` is a queue for the operator UI to poll, not the record
of truth. Unanswered approvals expire closed after 24 hours.

## Keeping the two implementations in step

The n8n Code node mirrors `bots/rfed_audit_bot.py`. `tests/test_rfed_hash_parity.py`
pins them together: it extracts the canonicaliser from this JSON, runs it under
node, and asserts byte-identical output and identical chain hashes against the
Python core — plus that the risk tables and policy version match.

The subtle trap it guards: Python renders floats via `repr()` (`0.0`), while
`JSON.stringify(0.0)` gives `0`. The Code node wraps float-typed fields in
`PyFloat` to compensate. Remove that and every hash the workflow writes becomes
unverifiable — silently. Change one side, run the parity test, change the other.
