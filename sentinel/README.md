# SENTINEL — Phase-One Governance Shell

A defense-grade, **fail-closed** reference implementation of permission-aware
retrieval for the PERCIVAL / JARVIS OS control plane. It proves the Phase-One
exit milestone: *the Governance Shell catches and blocks unauthorized agent
retrieval in a restricted scope.*

## PERCIVAL named agents
See [`PERCIVAL_AGENTS.md`](./PERCIVAL_AGENTS.md). Recent additions:
- **Purple-Team** — detection-engineering / SOC exercise driver
  ([`PURPLE_TEAM_PLAYBOOK.md`](./PURPLE_TEAM_PLAYBOOK.md) ·
  `sentinel/sentinel/purpleteam.py`).
- **PFAS** — Ontario compliance + decision intelligence agent for water /
  property / infrastructure ([`PERCIVAL_PFAS_BRIEF.md`](./PERCIVAL_PFAS_BRIEF.md)).
  Anchored to Health Canada's interim drinking-water objective (30 ng/L,
  sum of 25 PFAS); fail-closed; no person identification.
  - `sentinel/sentinel/pfas.py` — risk scoring + compliance package
  - `sentinel/sentinel/pfas_ingest.py` — long-form lab **CSV ingester**
  - `sentinel/sentinel/pfas_pdf.py` — **text-PDF profile** (EPA 533 style;
    rejects image/encrypted PDFs)
  - `sentinel/sentinel/pfas_export.py` — **evidence-pack exporter**
    (client-ready Markdown + JSON)
  - `sentinel.html` — **map layer** + per-site drawer with **Download
    evidence pack** (in-browser .md + .json save)
  - demo GeoJSON + sample CSV under `assets/data/`

- **AEGIS** — lawful-access **compliance & rights-protection** agent
  ([`AEGIS_LEGAL_SHIELD_BRIEF.md`](./AEGIS_LEGAL_SHIELD_BRIEF.md) ·
  `sentinel/sentinel/legalshield.py`). Validates legal-process requests
  (warrants / production orders / subpoenas / preservation / emergency),
  minimizes disclosure to what's lawfully compelled, routes everything to
  counsel (fail-closed), and **refuses** to assist with evading or obstructing
  valid process. Not legal advice.

- **PHOENIX** — governed **autonomous recovery / self-healing** agent
  ([`PHOENIX_RECOVERY_BRIEF.md`](./PHOENIX_RECOVERY_BRIEF.md) ·
  `sentinel/sentinel/phoenix.py`). Runs the incident loop
  *detect → classify → contain → plan → gate → execute → verify → learn* under a
  fail-closed policy gate: only reversible, low-risk, low-blast, high-confidence
  steps auto-execute; data-corruption / security / payment incidents are
  escalation-only; a circuit breaker + incident memory prevent repeated-failure
  loops; and an incident only closes once an independent health probe verifies
  restoration. `python -m sentinel.phoenix_demo` narrates the scenarios;
  `tests/test_phoenix.py` proves the safety invariants.

## Charter-compliant capabilities (no person identification)

- **Command center** ([`../sentinel.html`](../sentinel.html)) — map-first
  situational awareness for owned sites: live owned-camera *presence* analytics,
  sensor/incident timelines, evidence cards (provenance · timestamp ·
  jurisdiction · confidence), and a command bar whose deny-path mirrors the
  policy gate (any person-identification query is refused + audited).
- **Anonymous presence analytics** (`sentinel/vision.py · PresenceMonitor`) —
  occupancy, tailgating, abandoned-object, and loitering events that count
  *that* people are present, never *who*. No identity, no biometric templates.
- **Consented access control** (`sentinel/vision.py · ConsentedAccessControl`) —
  verifies an enrolled, opt-in credential behind the policy gate (documented
  authorization + verified jurisdiction), grants pending human review, and never
  identifies non-consenting people.

## Privacy charter (SENTINEL persona)

SENTINEL is a privacy-first geospatial and OSINT intelligence platform for
authorized asset protection, compliance, situational awareness, and emergency
response. It supports lawful satellite imagery, owned-site imagery, authorized
sensor feeds, and approved public-source intelligence for organizations, brands,
domains, facilities, and infrastructure.

SENTINEL **does not identify, locate, track, profile, or de-anonymize private
individuals**. It **fails closed** on covert access, deceptive access,
unauthorized scraping, biometric misuse, and geospatial fusion intended to
re-identify people.

Its rules ([`SENTINEL_CHARTER.md`](./SENTINEL_CHARTER.md), charter v2.1) are
**enforced in code** by [`sentinel/policy.py`](./sentinel/policy.py) — a
fail-closed gate that runs *before any feed or record is touched*; role +
purpose + jurisdiction + approved-source checks are required, sensitive work
escalates to human review, and every decision carries an `audit_ref`.

```python
from sentinel.policy import PrivacyPolicy, RequestContext
PrivacyPolicy().evaluate(RequestContext(
    actor_role="soc_analyst", purpose="perimeter intrusion monitoring",
    data_source="owned_camera_network", intent="monitor"))  # -> ALLOW
```

## The assurance gate (SABER-aligned)

```
Execution = Permitted  iff  (C ≥ τ) ∧ (R_data ⊆ P_user) ∧ (S_threat < ε)
          = Denied     otherwise   (and Denied if ANY term is uncomputable)
```

- **C** — request/agent confidence (`τ` default 0.60)
- **R_data ⊆ P_user** — requested data within the user's permission boundary
- **S_threat** — adversarial-injection score from a secondary red-team scorer (`ε` default 0.50)
- **Fail-closed** — an RBAC/DB outage, a raised scorer, or any unverifiable term ⇒ **Denied**

## RBAC model (see `../docs/adr/0001-vector-rbac-model.md`)

Hybrid, defense-in-depth:

1. **Tenant** = hard partition (namespace/collection per tenant). Blast-radius
   containment, per-tenant delete + KMS key.
2. **Role / sensitivity** = ACL metadata pre-filter *inside* the partition
   (optimization that narrows candidates).
3. **Authority** = every returned `doc_id` is **re-authorized against Postgres
   RBAC** before any chunk reaches the LLM. A vector-layer bug or poisoned
   embedding metadata degrades to *missed results*, never *leaked results*.

## The trust loop (`sentinel/retrieval.py`)

```
ingest(query) → S_threat
   → resolve P_user (fail-closed)
   → Governance Shell gate (C, scope, S)
   → select tenant namespace (server-side)
   → fail-closed ACL filter (deny-all if P_user unresolved)
   → vector query (candidates)
   → RE-AUTHORIZE doc_ids vs Postgres RBAC   ← authoritative gate
   → assemble chunks + provenance + confidence band
   → append to hash-chained audit log
```

## Run

```bash
# Core trust loop — no external deps:
cd sentinel && python -m pytest -q          # 11 proof tests

# Optional HTTP layer:
pip install -r requirements.txt
uvicorn sentinel.app:app --reload
# curl -s localhost:8000/v1/retrieve -H 'Authorization: Bearer tok-acme-analyst' \
#      -H 'content-type: application/json' -d '{"query":"revenue report"}'
```

## What the tests prove (`tests/test_governance.py`)

| Property | Test |
|---|---|
| Authorized retrieval returns only in-scope docs | `test_authorized_retrieval_returns_only_in_scope` |
| Admin clearance unlocks sensitive doc | `test_admin_clearance_unlocks_sensitive_doc` |
| Clearance ceiling filters secrets | `test_clearance_boundary_filters_secret` |
| **Cross-tenant blocked even when the vector store leaks** | `test_cross_tenant_blocked_even_when_vector_store_leaks` |
| RBAC outage ⇒ fail-closed (deny, 0 chunks) | `test_failclosed_when_rbac_unavailable` |
| Prompt injection ⇒ denied | `test_prompt_injection_denied` |
| Low confidence ⇒ denied | `test_low_confidence_denied` |
| Custom thresholds enforced | `test_custom_thresholds_enforced` |
| Audit chain tamper-evident | `test_audit_chain_is_tamper_evident` |

## Production swap-ins

| Reference | Production |
|---|---|
| `InMemoryRBAC` | `PostgresRBAC` (`schema.sql`, short statement timeout) |
| `InMemoryVectorStore` | Pinecone (namespace=tenant) or Milvus (partition-key=tenant) |
| `embed()` hashing stub | real embedding model |
| `HeuristicRedTeam` | dedicated red-team / injection-classifier model |
| in-memory `AuditLog` | append-only Postgres table + periodic anchoring |
