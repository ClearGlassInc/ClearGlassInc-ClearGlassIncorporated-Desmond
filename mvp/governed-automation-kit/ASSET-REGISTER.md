# Product Asset Register — Governed AI Automation Operating Kit

Required by the MVP approval, §4 (originality and IP) and §7.2. Every component shipped
in this product must appear here with its origin, author, licence and approval status.

**Register status:** 8 assets. All original ClearGlass work. No third-party templates,
no open-source dependencies, no external licences, no customer or credential data.

---

## Assets

| ID | Asset | Path | Origin | Author | Licence | Version | Approval |
|----|-------|------|--------|--------|---------|---------|----------|
| A-01 | Automation Opportunity Assessment | `components/01-opportunity-assessment.md` | Original | ClearGlass Inc. | ClearGlass proprietary (terms pending) | 0.1.0 | Drafted — owner review pending |
| A-02 | Workflow Inventory Template | `components/02-workflow-inventory.md` | Original | ClearGlass Inc. | ClearGlass proprietary (terms pending) | 0.1.0 | Drafted — owner review pending |
| A-03 | Automation Prioritization Matrix | `components/03-prioritization-matrix.md` | Original | ClearGlass Inc. | ClearGlass proprietary (terms pending) | 0.1.0 | Drafted — owner review pending |
| A-04 | Automation Risk-Tiering Framework | `components/04-risk-tiering-framework.md` | Original; **derived from ClearGlass-owned production source** (see note 1) | ClearGlass Inc. | ClearGlass proprietary (terms pending) | 0.1.0 | Drafted — owner review pending |
| A-05 | Human Approval-Gate Model | `components/05-approval-gate-model.md` | Original; derived from A-04 | ClearGlass Inc. | ClearGlass proprietary (terms pending) | 0.1.0 | Drafted — owner review pending |
| A-09 | Automation ROI and Effort Calculator | `tools/automation_roi.py` | Original | ClearGlass Inc. | ClearGlass proprietary (terms pending) | 0.1.0 | Built + tested — owner review pending |
| A-09T | Calculator regression tests | `tests/test_automation_roi.py` | Original | ClearGlass Inc. | Internal — not shipped to customers | 0.1.0 | Passing (19 tests) |
| A-00 | MVP Design Execution Report | `EXECUTION-REPORT.md` | Original | ClearGlass Inc. | Internal — not shipped to customers | 0.1.0 | Delivered |

### Specified, not yet drafted

| ID | Asset | Blocking |
|----|-------|----------|
| A-06 | Automation Governance Checklist | Nothing — inputs complete (A-05) |
| A-07 | Evidence and Provenance Checklist | Nothing |
| A-08 | Security and Privacy Readiness Checklist | A-07 |
| A-10 | Standard Operating Procedure Templates | A-05, A-06 |
| A-11 | Automation Implementation Roadmap (30/60/90) | A-06, A-10 |

---

## Note 1 — provenance of the risk model (A-04)

A-04 is the product's differentiating asset, so its provenance is stated precisely.

Its tier thresholds, escalation triggers and fail-closed default are **generalised from
ClearGlass's own production source**, which ClearGlass wholly owns:

- `control-plane/app/governance.py` — 0–100 action scoring, tier boundaries
  (`>=90` critical, `>=60` high, `>=30` medium), payload escalators, the
  `ALWAYS_ESCALATE` set, and the unknown-action default of 85.
- `bots/rfed_audit_bot.py` — the same shape applied to agentic actions, with a
  SHA-256 hash-chained ledger.

**No customer configuration, credential, tenant name, incident record, or engagement
detail is carried across.** What is reused is the *structure* — the thresholds and the
escalation logic — which is ClearGlass's own design.

The coverage percentages in the calculator (95 / 80 / 50 / 30% by tier) and the review
minutes (0 / 0.5 / 2 / 5) are **new planning assumptions written for this product**. They
are not measurements taken from any system, and both the code and the product output say
so. They must not be described as observed or benchmarked figures.

---

## Duplicate-content and third-party review

| Check | Result |
|---|---|
| Marketplace titles, descriptions, images or layouts copied | None — no marketplace content was consulted |
| Third-party templates or workflows included | None |
| Open-source code or dependencies included | None — `automation_roi.py` is Python standard library only |
| Competitor material referenced or adapted | None |
| Customer data, credentials, tokens or private repository content | None |
| Material with uncertain ownership or restricted redistribution | None — excluded by rule |
| Personal data of any individual | None |

`automation_roi.py` imports only `argparse`, `json`, `sys`, `dataclasses` and `typing`.
There is no dependency manifest for this product, and therefore no third-party licence
obligation.

---

## Exclusions applied

Deliberately kept out of the product, per the approval:

- ClearGlass client names, engagement details, findings and environments.
- Any credential, token, key, endpoint or private configuration.
- The `control-plane/` source itself. The kit teaches the model; it does not ship the
  implementation. Shipping the source would give away the delivery capability that the
  service business sells.
- Any figure presented as a benchmark, industry average or measured outcome.

---

## Change control

Bump the asset's version and add a row here when its content changes. An asset whose
provenance or licence status changes must be re-reviewed before release, not amended
in place.
