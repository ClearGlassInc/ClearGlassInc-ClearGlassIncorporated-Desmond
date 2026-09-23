# Claims Register — Governed AI Automation Operating Kit

Required by the MVP approval, §7.6. Every claim the product or its marketing could make
is assessed here before it is written anywhere a customer can read it.

**Rule applied:** a claim ships only if it is true, evidenced, and would survive a
customer asking "prove it". Anything that would not is rewritten or dropped. A claim is
never upgraded because it seems probable.

**Status:** 11 assessed — 6 approved as worded, 3 rewritten, 2 rejected.

---

## C-01 — Derived from a production system

| | |
|---|---|
| **Proposed** | "Built on the governance model ClearGlass runs in production." |
| **Evidence** | `control-plane/app/governance.py` (0–100 scoring, tier thresholds, `ALWAYS_ESCALATE`, fail-closed default 85); `bots/rfed_audit_bot.py` (hash-chained decision ledger). Both enforced by tests in `control-plane/tests/test_governance.py` and `tests/test_rfed_hash_parity.py`. |
| **Approved wording** | "The risk-tiering model in this kit is generalised from a governed automation system ClearGlass built and runs, not written for a template." |
| **Prohibited** | "Battle-tested", "proven at scale", "trusted by leading firms", any customer count or deployment count. |
| **Status** | **APPROVED** |

## C-02 — What the kit does

| | |
|---|---|
| **Proposed** | "Helps teams organize, document, prioritize and prepare automation initiatives." |
| **Evidence** | Components 1–5 and the calculator do exactly this. |
| **Approved wording** | As proposed — it is the approval's own scope language. |
| **Prohibited** | "Makes your business AI-ready", "automates your business". |
| **Status** | **APPROVED** |

## C-03 — Savings from the calculator

| | |
|---|---|
| **Proposed** | "Calculate the ROI of your automation." |
| **Problem** | "Calculate ROI" implies the number is a result. It is arithmetic on the buyer's own guesses. |
| **Rewritten** | "Estimate time, cost and payback from your own assumptions — including the review time a gated workflow never stops needing." |
| **Mandatory companion** | The estimates disclaimer, on every output. Enforced in code (`DISCLAIMER`) and pinned by `tests/test_automation_roi.py::test_every_output_path_carries_the_disclaimer`. |
| **Prohibited** | "Save X hours", "typical customers save", "guaranteed payback", any named percentage of savings. |
| **Status** | **REWRITTEN — approved as rewritten** |

## C-04 — The governance insight

| | |
|---|---|
| **Proposed** | "Most automation ROI models overstate returns because they ignore approval overhead." |
| **Evidence** | Demonstrated, not asserted: the calculator's own critical-tier example returns a negative monthly saving and a `DO_NOT_AUTOMATE` verdict. Pinned by `test_a_gated_workflow_can_be_worth_less_than_doing_it_by_hand`. |
| **Approved wording** | "An hours-removed calculation prices the work and ignores the decision. This one prices the approval gate too — which is why some workflows in it come back as *don't automate this*." |
| **Prohibited** | "Most companies waste X% on automation" — no such figure has been measured. |
| **Status** | **APPROVED** |

## C-05 — Risk tier coverage figures

| | |
|---|---|
| **Proposed** | "Low-risk workflows are 95% automatable; critical-risk only 30%." |
| **Problem** | Reads as measured. It is a planning assumption written for this product. |
| **Rewritten** | "The kit assumes automation removes less hands-on time as risk rises (95% at low risk down to 30% at critical). These are starting assumptions for planning — replace them with your own measurements as you get them." |
| **Prohibited** | Presenting 95/80/50/30 as benchmarks, research, or observed industry figures. |
| **Status** | **REWRITTEN — approved as rewritten** |

## C-06 — Compliance

| | |
|---|---|
| **Proposed** | "Helps you meet AI governance and compliance requirements." |
| **Problem** | Implies regulatory sufficiency. ClearGlass cannot certify any customer's compliance, and the approval forbids the claim. |
| **Rewritten** | "Helps you document ownership, approval checkpoints and decision records — the kind of material a compliance or audit conversation tends to ask for." |
| **Prohibited** | "Compliant", "compliance-ready", "meets ISO/SOC 2/PHIPA/NIST/EU AI Act requirements", "audit-proof". |
| **Status** | **REWRITTEN — approved as rewritten** |

## C-07 — Security

| | |
|---|---|
| **Proposed** | "Makes your automation secure." |
| **Assessment** | A planning document cannot secure anything. No evidence exists or could exist. |
| **Status** | **REJECTED — do not use in any form.** Component 8 is a *readiness planning checklist*, and says so on its face. |

## C-08 — Outcomes and results

| | |
|---|---|
| **Proposed** | "Teams using this kit ship automation faster." |
| **Assessment** | Zero customers. Zero usage data. The claim would be fabricated. |
| **Status** | **REJECTED.** Not re-assessable until real customer outcomes exist, with evidence and permission to cite them. |

## C-09 — Originality

| | |
|---|---|
| **Proposed** | "100% original ClearGlass material." |
| **Evidence** | `ASSET-REGISTER.md` — every asset registered as original; duplicate-content and third-party review recorded; calculator is Python standard library only. |
| **Approved wording** | "Every worksheet, framework and tool in this kit is original ClearGlass work. No third-party templates, no repackaged content." |
| **Status** | **APPROVED** |

## C-10 — Support

| | |
|---|---|
| **Proposed** | *(none yet)* |
| **Assessment** | No support commitment may be published until the owner sets one (Execution Report §7, item 5). Stating a response time before one is chosen creates an obligation ClearGlass has not agreed to. |
| **Status** | **BLOCKED — no support claim may be made until the policy is set.** |

## C-11 — Price and value

| | |
|---|---|
| **Proposed** | "Worth $5,000 of consulting for $249." |
| **Assessment** | A value comparison with no basis. No consulting engagement has been priced against this content. |
| **Status** | **REJECTED.** State the price. Let it stand on what the kit contains. |

---

## Enforcement

Before any asset, landing page, listing or post is drafted for external use, its claims
are checked against this register. A claim not listed here has not been approved, and a
new claim needs a row, evidence and an owner decision before it is written.

Two claims are enforced in code rather than by discipline, because discipline is what
fails silently:

- **C-03's disclaimer** — `automation_roi.py::DISCLAIMER`, asserted on every output path.
- **C-04's insight** — asserted by a test that fails if the approval gate stops affecting
  the result, which is the point at which the product would quietly lose its claim.
