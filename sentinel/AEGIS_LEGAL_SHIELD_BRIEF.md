# AEGIS — Legal-Process Shield (PERCIVAL agent)

> **What it is:** a lawful-access **compliance & rights-protection** agent. It
> protects ClearGlass Inc. and its principals (incl. Desmond Otieno Odhiambo) by
> ensuring every legal-process request is **validated, minimized, routed to
> counsel, and audited** — and by flagging defective or overbroad demands so they
> can be lawfully challenged.
>
> **What it is NOT:** it does **not** evade, obstruct, or defeat valid warrants
> or lawful oversight. It refuses to assist with destroying/altering evidence
> under hold, concealing assets, tipping off a subject, or evading process
> (`guard_action → REFUSE_UNLAWFUL`).
>
> **Not legal advice.** A licensed lawyer in the relevant jurisdiction must
> review every request before any response or disclosure. AEGIS is **fail-closed**:
> it never authorizes disclosure on its own — counsel review is always required.

Executable: `sentinel/sentinel/legalshield.py` · tests: `sentinel/tests/test_legalshield.py`.

## Why this is the right protection under a lawful-access regime

When a bill expands lawful-access tools (warrants, production orders, oversight),
the durable protection for an organization is **process discipline + rights
assertion**, not evasion:

1. **Validate** every request (issuing authority, jurisdiction, signature,
   warrant/file number, expiry, scope particularity).
2. **Challenge** what's defective, overbroad, or expired (move to quash/narrow).
3. **Minimize** — disclose only the specific items lawfully compelled, never more.
4. **Counsel-in-the-loop** — no disclosure without a lawyer's sign-off.
5. **Audit + transparency** — immutable register of every request and response.
6. **Assert rights** — privilege, protective orders/sealing, user notice where
   lawfully permitted.

## Decision model

| Request kind | AEGIS outcome |
|---|---|
| Valid, signed, scoped warrant / production order / subpoena | `COMPLY_PENDING_COUNSEL` — minimized to scope, **after** counsel sign-off |
| Defective / overbroad / expired / unsigned | `CHALLENGE` — route to counsel to quash or narrow |
| Preservation demand | `PRESERVE_IN_PLACE` — legal hold; never delete/alter; no disclosure |
| Emergency disclosure request | `ACKNOWLEDGE_ROUTE_COUNSEL` — counsel verifies statutory basis + exigency; never auto-disclose |
| Informal / voluntary request (no compulsion) | `REFUSE_NO_LEGAL_BASIS` — don't volunteer data; require lawful process |
| Our own obstruction action | `REFUSE_UNLAWFUL` — AEGIS will not assist |

Every assessment sets `requires_counsel_review = True`, carries the disclaimer,
tags `protected_principal` when ClearGlass / Desmond is named, lists `objections`
to consider, and writes a hash-chained audit entry.

## Proactive, lawful posture (`posture_recommendations()`)
Data minimization + retention limits · encryption (keys you control) ·
least-privilege + access logging · data inventory/map for precise scoping ·
vendor DPAs + residency · legal-hold process + custodian-of-records + counsel
contact · transparency reporting · lawful user notice.

## Usage

```python
from sentinel.legalshield import LegalProcessShield, LegalRequest, RequestKind

shield = LegalProcessShield()
a = shield.assess(LegalRequest(
    id="LR-2026-014", kind=RequestKind.WARRANT,
    issuing_authority="Ontario Court of Justice", jurisdiction="ON, CA",
    target="ClearGlass Inc.", scope=("account X access logs 2026-01..03",),
    signed=True, warrant_number="CR-2026-0420"))
print(a.outcome, a.permitted_disclosure, a.audit_ref)
# COMPLY_PENDING_COUNSEL ['account X access logs 2026-01..03'] <audit>

shield.guard_action("destroy_evidence")   # -> REFUSE_UNLAWFUL
```

## Register, transparency report & shared audit
- **Register** — `LegalProcessShield.register` accumulates every `(request,
  assessment)` row for downstream reporting.
- **Transparency report** — `sentinel/sentinel/transparency.py`
  (`build_report` → `report_markdown` / `report_json`) summarizes the register
  into publishable **aggregate counts** (by type, by outcome, challenges,
  refusals, protected-principal mentions) — never request content or disclosed
  data.
- **Shared audit stream** — pass a shared `AuditLog` to the shield
  (`LegalProcessShield(audit=system_ledger)`) to wire AEGIS decisions into the
  wider SENTINEL audit stream; the hash chain stays intact across actors.
- **UI** — [`aegis.html`](../aegis.html): a local-only intake form + register +
  one-click transparency-report download (mirrors the Python decision model).
  Reachable from the PERCIVAL HUD (**⚖ AEGIS**).

## Boundaries
- AEGIS is a **workflow aid**, not a lawyer. Engage qualified counsel.
- It assists **lawful compliance and the assertion of legitimate rights** only.
- It will not help defeat valid legal process or lawful oversight.
