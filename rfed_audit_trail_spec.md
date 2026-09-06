# ClearGlass RFED™ — Audit-Trail Module Specification

**Status:** shipped, dry-run by default
**Policy version:** `rfed-1.0.0`
**Logic core:** `bots/rfed_audit_bot.py` (stdlib only)
**Orchestration:** `deployment/rfed/workflow_rfed_audit_trail.json` (n8n)
**Agent:** `agents/rfed_audit/` (Cursor / Claude agent stack)
**Tests:** `tests/test_rfed_audit_bot.py`, `tests/test_rfed_hash_parity.py`

---

## 1. What RFED is

**RFED — Recorded Factual Evidence of Decision.**

A tamper-evident audit trail for agentic workflows. Every action a model
influences is recorded as a four-segment record and sealed into a SHA-256 hash
chain.

The problem it solves: when an AI system takes an action in a client
environment, "the agent did it" is not an answer anyone can act on. An auditor,
an insurer, or a client's counsel asks three questions:

1. **Which model decided this?** — exact model id, parameters, and when.
2. **What did it actually know?** — the facts it was given, by digest, from an
   allow-listed source.
3. **Who said yes?** — the human approval, or the policy that permitted it to
   run unattended.

RFED answers all three from a single record, and makes the answer hard to
retroactively edit.

> **Naming note.** "RFED™" arrived as a brief without an expansion. It is
> implemented here as *Recorded Factual Evidence of Decision*, which matches the
> stated success metric — logged evidence of model accountability. If ClearGlass
> means something else by the mark, the expansion is a one-line change in this
> spec and the module docstring; nothing in the mechanism depends on it.

## 2. The invariant

    read-only analysis → draft → human approval → execution

This mirrors the commerce OS safety model in
`clearglass-commerce/control-plane/app/governance.py` deliberately. One
governance idea, applied in two places, so operators only have to learn it once.

## 3. Record structure

| Segment | Field | Purpose |
|---------|-------|---------|
| **R** — Request | `actor`, `workflow`, `action`, `target`, `intent`, `correlation_id`, `input_digest` | What was asked, by whom |
| **F** — Facts | `[{source, reference, content_digest, retrieved_at, trusted}]` | What the model was actually given |
| **E** — Evidence | `model_id`, `provider`, `temperature`, `max_tokens`, `prompt_digest`, `output_digest`, `output_excerpt`, `confidence`, `citations`, token counts | What the model was, and what it produced |
| **D** — Decision | `score`, `tier`, `route`, `requires_approval`, `reasons`, `approved_by`, `approved_at` | How it was routed, and who signed |

Plus the chain fields: `record_id`, `occurred_at`, `policy_version`, `prev_hash`,
`chain_hash`.

`policy_version` is recorded per row so a decision can be replayed against the
policy that was live when it was made — not the policy as it stands today.

## 4. The hash chain

```
chain_hash = sha256( prev_hash || canonical_json(record_body) )
```

- Genesis `prev_hash` is 64 zeroes.
- `canonical_json` pins key order, separators, and non-ASCII escaping, so the
  same logical record hashes identically on any machine.
- Editing any record invalidates its own seal **and** every link after it.
  `verify()` reports the first break and its index.
- Deleting a record breaks the `prev_hash` continuity of its successor.

Three attacks this defends against, all covered by tests:

| Attack | Detected by |
|--------|-------------|
| Edit a payload after the fact | recomputed seal ≠ stored seal |
| Flip a gated decision to `auto_executed` | same — the decision is inside the hashed body |
| Delete an inconvenient record | successor's `prev_hash` no longer matches the head |

### Cross-implementation parity

The n8n Code node and the Python core must produce identical hashes, or a record
sealed in production cannot be verified later. The trap: Python renders floats
via `repr()` (`0.0`), while `JSON.stringify(0.0)` gives `0`. The Code node wraps
float-typed fields in a `PyFloat` sentinel to compensate.

`tests/test_rfed_hash_parity.py` extracts the canonicaliser from the workflow
JSON, runs it under node, and asserts byte-identical canonical form and identical
chain hashes — including non-ASCII escaping. It also asserts the risk tables and
policy version match across both.

## 5. Risk model

| Tier | Score | Route |
|------|-------|-------|
| low | 0–29 | auto-execute + log |
| medium | 30–59 | queue for review |
| high | 60–89 | approval required |
| critical | 90–100 | approval required, highest scrutiny |

**Base risk** by action — read-only analysis at 0–15, reversible internal changes
at 30–45, external effects at 62–78, and identity/credential/remote-execution at
92–100. Full table in `bots/rfed_audit_bot.py::ACTION_RISK`.

**Always escalate**, regardless of score: `modify_access_policy`,
`grant_privileged_access`, `rotate_credentials`, `execute_remote_command`,
`disable_security_control`, `export_client_data`, `modify_audit_log`,
`push_config_change`, `quarantine_endpoint`, `send_client_comms`.

**Never automate**: `modify_audit_log`. Blocked outright, approved or not. A
workflow asking to rewrite the ledger is either broken or hostile.

### Accountability signals

These gate an action **on their own**, independent of base score. This matters:
a score bump alone can leave a low-base action under the HIGH threshold and let
it auto-execute, which would contradict the reason recorded against it.

| Signal | Why it gates |
|--------|-------------|
| No citations | Output is ungrounded — there is nothing to audit it against |
| Confidence < 0.75 | The model itself is unsure |
| Injection markers in an untrusted fact | The context is hostile |
| Citation absent from supplied facts | Fabricated provenance |
| Unknown action | Fail closed at 85 |

Untrusted facts are scanned; trusted ones are not. Flagging curated sources would
train operators to ignore the signal.

## 6. Approvals

Approval **appends a new record**. It never mutates the original.

```python
gated  = ledger.append(request, facts, evidence)   # route=queued_for_approval
signed = approve(gated, "desmond@clearglassinc.com")
ledger.append_record(signed)                        # prev_hash = gated.chain_hash
```

The follow-on record carries the approver, the timestamp, and the original's
chain hash as its `input_digest` — so the approval is cryptographically bound to
the exact decision it authorises, not to a record id that could later point
somewhere else.

`approve()` refuses to sign a `blocked` record or one that never required
approval.

`rfed_approvals` is a queue for the operator UI to poll. It is not the record of
truth. Unanswered approvals expire closed after 24 hours.

## 7. Redaction

Emails, card numbers, SINs, bearer tokens, and API-key-shaped strings are
stripped from `output_excerpt` before the record is sealed, and the excerpt is
truncated to 500 characters. Full content is never stored — only its digest. The
ledger proves *what* the model said without becoming a second copy of the
client's sensitive data.

## 8. Zero-trust ingress

The workflow authenticates its caller before reading anything:

- HMAC-SHA256 over `{timestamp}.{raw_body}`, keyed on `RFED_WEBHOOK_SECRET`
- constant-time comparison (`crypto.timingSafeEqual`)
- 300-second replay window
- missing secret → the workflow refuses every proposal

A proposal that fails here never reaches the model, never touches the ledger, and
never costs a token.

## 9. Operations

```bash
# governance invariants + demo ledger (stdlib only, no DB)
python -m bots.rfed_audit_bot --self-check
python -m bots.rfed_audit_bot --self-check --write   # -> operations/output/rfed/

# verify a production ledger export
python -m bots.rfed_audit_bot --verify ledger.jsonl
python -m bots.rfed_audit_bot --summary ledger.jsonl

# machine-readable for CI
python -m bots.rfed_audit_bot --verify ledger.jsonl --json
```

Exit code is non-zero when the chain is broken, so this drops straight into a
scheduled gate.

Operator views ship with the schema: `rfed_pending_approvals` (what is waiting on
a human, worst-first) and `rfed_model_accountability` (per-model rollup:
decisions, routing mix, ungrounded count, mean confidence).

## 10. Deliberate limits

Stated plainly, because a governance module that oversells itself is worse than
none:

- **The chain proves integrity, not honesty.** It shows a record was not altered
  after sealing. It cannot show the facts were true when retrieved — that is what
  `content_digest` against an allow-listed source is for.
- **An operator with `UPDATE` on the table can still rewrite history** — they
  just cannot do it *invisibly*, because `verify()` will report the break. Deploy
  with a writer role that has no `UPDATE`/`DELETE` grant.
- **`confidence` is self-reported.** It is a useful gate, not a measurement. The
  citation checks are the harder control.
- **Injection detection is a keyword heuristic.** It raises the cost of the
  obvious attempts; it is not a parser and should not be described to clients as
  one.
- **Anchoring is not implemented.** Periodically publishing the head hash to an
  external witness would defend against a wholesale ledger replacement. Today the
  head lives only in the client's database.

## 11. Related

- `clearglass-commerce/control-plane/app/governance.py` — the commerce-side
  governor this mirrors
- `deployment/cashpulse/` — the n8n deployment pattern this follows
- `security/RMM_AUTH_BYPASS_HARDENING.md` — the zero-trust posture work that uses
  this module's `client_zero_trust` workflow
