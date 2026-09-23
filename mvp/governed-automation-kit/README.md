# Governed AI Automation Operating Kit — MVP (internal)

> **Internal design work. Not published, not listed, not priced live, not for sale.**
> Authorised by *Owner Approval — ClearGlass MVP Design* (internal design, development
> and validation preparation only). Every external, commercial, financial and
> account-changing action is held in the approval queue — see
> [`EXECUTION-REPORT.md`](EXECUTION-REPORT.md) §9.

A planning and governance toolkit for deciding **which** business automation to build and
**what oversight it needs** — before building it.

## Read this first

[`EXECUTION-REPORT.md`](EXECUTION-REPORT.md) — the design deliverable. Section 0 carries
a finding that outranks this product: the eight search-indexed `offers/*.html` pages
convert through `mailto:` while `store.html` already has one-click Stripe checkout.
Closing that gap is worth more than finishing this kit, and it needs owner approval
(item **AQ-1**).

## Contents

| | Component | State |
|---|---|---|
| 01 | [Automation Opportunity Assessment](components/01-opportunity-assessment.md) | Drafted |
| 02 | [Workflow Inventory Template](components/02-workflow-inventory.md) | Drafted |
| 03 | [Automation Prioritization Matrix](components/03-prioritization-matrix.md) | Drafted |
| 04 | [Automation Risk-Tiering Framework](components/04-risk-tiering-framework.md) | Drafted — **the core asset** |
| 05 | [Human Approval-Gate Model](components/05-approval-gate-model.md) | Drafted |
| 09 | [ROI and Effort Calculator](tools/automation_roi.py) | Built + tested |
| 06, 07, 08, 10, 11 | Governance / evidence / security checklists, SOP templates, 30-60-90 roadmap | Specified, not drafted |

Governance documents: [`ASSET-REGISTER.md`](ASSET-REGISTER.md) ·
[`CLAIMS-REGISTER.md`](CLAIMS-REGISTER.md)

## The calculator

```bash
python3 mvp/governed-automation-kit/tools/automation_roi.py --demo
python3 mvp/governed-automation-kit/tools/automation_roi.py --json --input tasks.json
```

Standard library only. It prices the **approval gate**, not just the hours removed —
which is why a critical-tier workflow in the demo set comes back `DO_NOT_AUTOMATE`. A
generic hours-removed calculator cannot produce that finding, and it is the product's
commercial argument.

Tests: `python3 -m pytest tests/test_automation_roi.py -q` (19 tests). They pin the
mandated estimates disclaimer on every output path, and fail if the gate ever stops
affecting the result — the point at which the product would quietly lose its claim.

## Where the risk model comes from

The tiers and escalators are generalised from ClearGlass's own production source —
`control-plane/app/governance.py` and `bots/rfed_audit_bot.py` — which ClearGlass wholly
owns. No customer configuration, credential or engagement detail is carried across, and
the control-plane source itself is **not** shipped: the kit teaches the model, it does
not hand over the delivery capability. See [`ASSET-REGISTER.md`](ASSET-REGISTER.md) note 1.

The calculator's coverage percentages (95/80/50/30 by tier) and review minutes are
planning assumptions written for this product. They are **not** measurements, and must
never be presented as benchmarks.

## Status

`PRE-COMMERCIAL-VALIDATION`. No verified customer, conversation, proposal or payment
exists for this product. Nobody has been asked whether they would pay for it. Pricing
options are proposed in the Execution Report §10 and none is activated.
