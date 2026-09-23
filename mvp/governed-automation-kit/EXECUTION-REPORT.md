# MVP Design Execution Report — Governed AI Automation Operating Kit

**Status:** Internal design deliverable. Nothing in this package is published, listed,
priced live, or offered for sale.
**Date:** 2026-09-23
**Authority:** Owner Approval — ClearGlass MVP Design (internal design, development and
validation preparation only).
**Commercial state at time of writing:** `PRE-COMMERCIAL-VALIDATION`. No verified
customer, contract, proposal, conversation or payment record has been supplied for this
product. Every figure below is an assumption, and is marked as one.

---

## 0. The finding that outranks this report

The approval directs internal MVP design. The Execution-First Revenue Control directive
says *sell before building*, and requires that a concrete revenue action be preferred
over discretionary work. Both were applied, and they disagree about what matters most
this week. The disagreement is preserved rather than resolved, per the conflict rule.

**ClearGlass already sells five service engagements, and two storefronts convert them
very differently.**

| Surface | Buyer's next step | Evidence |
|---|---|---|
| `store.html` | One click to Stripe checkout, plus Interac e-Transfer fallback | 4 live `buy.stripe.com` links in `data/store/catalog.json` + `store.html` |
| `offers/*.html` (8 pages in `sitemap.xml`) | Compose an email asking Desmond to send a payment link | `mailto:` hrefs in `security-quick-audit.html`, `hardening-sprint.html`, `phipa-readiness.html` |

The eight pages submitted to search engines are the ones that ask a buyer for a
$249 product to write an email and wait. The one-click path exists, is already wired,
and is not what an organic visitor lands on.

That is a conversion gap on the indexed surface, and closing it is a website-page
modification — **explicitly not authorized** by section 6 of the approval. It is
therefore filed as approval-queue item **AQ-1** in section 9 and is not actioned here.

**Assessment: building this kit is not the highest-value commercial action available.**
It is the highest-value *authorized* action, which is a different claim. Under the
No-Opportunity Rule (no authorization to contact anyone → build the pipeline), proceeding
with internal design is correct. The owner should know it was the second-best option.

---

## 1. Approved Scope Confirmation

Confirmed in scope, and what this package actually is:

- An original, ClearGlass-owned planning and governance toolkit for business automation.
- Positioned as a structured decision system, **not** a prompt pack or workflow bundle.
- Sold to operators, agencies, founders and technical teams who need to decide *which*
  automation to build and *what* oversight it needs — before building it.

Confirmed out of scope, and not present in any asset:

- No guarantee of revenue, savings, compliance, security, performance or ROI.
- No legal, tax, financial, medical, insurance or regulated-compliance advice.
- No claim to certify, secure or validate a customer's environment.
- No third-party templates, marketplace copy, competitor material, customer data,
  credentials or licensed content.

Scope statement carried on the product:

> This product provides general business-process planning, workflow documentation,
> automation-prioritization, governance, and implementation-readiness materials. It does
> not provide legal, tax, financial, compliance, security-certification, or custom
> implementation advice.

### Differentiation, stated honestly

The kit's defensible claim is narrow and true: **its risk model is extracted from a
governance system ClearGlass actually runs**, not invented for a product.

`control-plane/app/governance.py` scores every proposed action 0–100, tiers it
(`>=90` critical, `>=60` high, `>=30` medium, else low), applies escalators for
money-delta, bulk scope and low confidence, holds an always-escalate set for financial,
fulfillment and outbound actions, and fails unknown actions closed at 85.
`bots/rfed_audit_bot.py` applies the same shape to agentic actions with a SHA-256 hash
chain. Both are enforced by tests.

Every competitor selling an "AI governance template" is selling a document. This sells a
model with a working implementation behind it. That is the entire commercial argument,
and it is the one thing that must not be diluted.

---

## 2. Product Asset Register

Full register with origin, author, licence and approval status: [`ASSET-REGISTER.md`](ASSET-REGISTER.md).

Summary: 8 assets created, all original ClearGlass work, no third-party dependencies, no
external licences, no customer or credential data. Four components drafted, four
specified but not yet drafted.

---

## 3. Proposed Product Table of Contents

| # | Component | State |
|---|---|---|
| 1 | Automation Opportunity Assessment | **Drafted** — `components/01-opportunity-assessment.md` |
| 2 | Workflow Inventory Template | **Drafted** — `components/02-workflow-inventory.md` |
| 3 | Automation Prioritization Matrix | **Drafted** — `components/03-prioritization-matrix.md` |
| 4 | Automation Risk-Tiering Framework | **Drafted** — `components/04-risk-tiering-framework.md` |
| 5 | Human Approval-Gate Model | **Drafted** — `components/05-approval-gate-model.md` |
| 6 | Automation Governance Checklist | Specified, not drafted |
| 7 | Evidence and Provenance Checklist | Specified, not drafted |
| 8 | Security and Privacy Readiness Checklist | Specified, not drafted |
| 9 | Automation ROI and Effort Calculator | **Built and tested** — `tools/automation_roi.py` |
| 10 | Standard Operating Procedure Templates | Specified, not drafted |
| 11 | Automation Implementation Roadmap (30/60/90) | Specified, not drafted |
| 12 | Original Illustrative Workflow Examples | **Drafted** — embedded in components 1–5 and the calculator's demo set |

Six of twelve components are complete. The report does not describe the remaining six as
finished, and the kit is not releasable until they are.

---

## 4. Build Sequence and Dependencies

Component 4 (risk tiering) is the root dependency. Components 3, 5 and 9 all consume its
tiers, so it was built first and the rest derive from it.

```
04 Risk-Tiering  ──┬──►  03 Prioritization Matrix
   (root)          ├──►  05 Approval-Gate Model  ──►  06 Governance Checklist
                   └──►  09 ROI Calculator  ──►  11 Roadmap
02 Workflow Inventory  ──►  01 Opportunity Assessment  ──►  03
07 Evidence/Provenance  ──►  08 Security & Privacy Readiness
10 SOP Templates  ── depends on 05 + 06 ──►  11 Roadmap
```

Order for the remaining work: 06 → 07 → 08 → 10 → 11. Each has its inputs complete.

---

## 5. Claims Register

Full register with proposed claim, evidence source, approved wording, prohibited wording
and owner approval status: [`CLAIMS-REGISTER.md`](CLAIMS-REGISTER.md).

Summary: 11 claims assessed. 6 approved as worded, 3 rewritten to remove an unsupported
guarantee, 2 rejected outright. No claim in any drafted asset is currently unsupported.

---

## 6. Top Technical and Commercial Risks

| # | Risk | Severity | Basis |
|---|---|---|---|
| R1 | **Zero validated demand.** Nobody has been asked whether they would pay for this. | **High** | State record: no verified lead, conversation or proposal |
| R2 | **The indexed storefront converts worse than the unindexed one.** Effort here does not fix that. | **High** | §0 above; `sitemap.xml` + `offers/*.html` |
| R3 | **Category is crowded and cheap.** "Automation templates" is a race to the bottom; only the production-derived governance model escapes it. | **High** | Positioning judgement — *unverified*, no market study performed |
| R4 | **Support burden is unmodelled.** A kit sold to non-technical operators generates questions. No support cost is priced. | Medium | No support policy drafted yet |
| R5 | **Buyer may want the implementation, not the plan.** The kit could cannibalise attention from the $2,500 Hardening Sprint rather than feed it. | Medium | Existing offers in `data/store/catalog.json` |
| R6 | **Calculator assumptions are defensible but not measured.** Tier coverage (95/80/50/30%) and review minutes are reasoned estimates. | Medium | `tools/automation_roi.py` — labelled as assumptions in code and output |
| R7 | **One catalog checkout link uses `book.stripe.com`,** not the `buy.stripe.com` used by the other four. Accepted by `store.html`'s regex, so not broken — but unverified end to end. | Low | `data/store/catalog.json:65` |

---

## 7. Missing Inputs Required From Owner

Blocking the kit's completion:

1. **Price.** No price is set. Options in §10; the owner picks, or the kit cannot be listed.
2. **Delivery format.** PDF bundle, Notion workspace, GitHub repo, or web pages? Changes packaging, support burden and refund exposure.
3. **Refund policy.** A digital product needs a stated position before it is sold.
4. **Licence terms.** Single user, team, or agency-resale? Determines pricing tiers.
5. **Support commitment.** Email only? Response window? This is the main unpriced cost.

Blocking anything commercial:

6. **A decision on AQ-1** (the offers-page conversion gap). This is worth more than items 1–5.
7. **One real conversation** with an operator who has the problem. Until then R1 stands and
   everything here is a hypothesis with a nice table of contents.

---

## 8. Internal Work That Can Begin Immediately

No further approval needed, all internal:

- Draft components 6, 7, 8, 10, 11 (§4 sequence).
- Extend the calculator with a portfolio CSV input and a sensitivity range.
- Draft the licence, refund, support and privacy documents for owner/legal review.
- Draft the landing page **as a file, unpublished and unlinked**.
- Write QA criteria and run the internal QA pass.
- Draft the launch-risk register and the payment-reconciliation plan.

---

## 9. Actions Explicitly Blocked Pending Separate Approval

Fail-closed. None of these have been performed, and none will be without a separate,
explicit authorization.

| ID | Blocked action | Why it is blocked | Value if approved |
|---|---|---|---|
| **AQ-1** | Point the 8 indexed `offers/*.html` pages at the already-live Stripe checkout links | §6 — modifying a website/product page | **Highest.** Removes an email round-trip from every organic buyer |
| AQ-2 | Publish the landing page or any listing | §6 — publishing external content | Required to sell at all |
| AQ-3 | Create a Stripe payment link or price for this kit | §6 — payment/checkout activation | Required to take money |
| AQ-4 | Any outreach, email, DM or marketplace message | §6 — external communication | Required to validate R1 |
| AQ-5 | Create or connect any marketplace, analytics or payment account | §6 — account modification | Required for fulfillment |
| AQ-6 | Verify the `book.stripe.com` link by loading it | Touching a live payment surface | Confirms R7 |
| AQ-7 | Represent the kit as validated, selling, or customer-tested | §6 and the anti-fabrication rule | Never approvable — the claim would be false |

---

## 10. Estimated Internal Readiness Criteria

The kit is ready for a **launch review** — not launch — when all of the following hold.
Six are met.

- [x] Every drafted asset is original ClearGlass work, registered with origin and licence
- [x] No customer, personal, credential or third-party restricted data is present
- [x] Every claim is supported, rewritten, or removed (`CLAIMS-REGISTER.md`)
- [x] The mandated estimates disclaimer appears on every calculator output path
- [x] The calculator's arithmetic is pinned by tests (`tests/test_automation_roi.py`, 19 tests)
- [x] Pricing is proposed but not activated
- [ ] All twelve components drafted (6 of 12)
- [ ] Licence, refund, support and privacy documents drafted
- [ ] Internal QA pass completed against written criteria
- [ ] Landing page drafted (unpublished)
- [ ] Launch-risk register and payment-reconciliation plan drafted

### Pricing options — proposed, not activated

All figures are estimates. None is live. None has been tested against a buyer.

| Option | CAD | Buyer | Scope | Support burden | Risk |
|---|---|---|---|---|---|
| A — Entry | $79 | Solo operator, founder | Full kit, self-serve | Low; expect email questions | Underprices the governance model; anchors low |
| B — Standard | $249 | Small team, agency | Full kit + calculator + SOP templates | Medium | Matches the existing Quick-Audit price — may confuse the two |
| C — Team licence | $599 | 10+ seat org | Kit + internal redistribution rights | Medium-high; licence questions | Needs licence terms drafted first (item 4) |
| D — Lead magnet | $0 | Anyone | Components 1–3 only; full kit gated | High volume, low value | Feeds the $2,500 Sprint instead of competing with it |

**Recommendation: D into B.** Give away the assessment and inventory, charge for the risk
model and calculator. It resolves R5 by making the kit a feeder for the service business
rather than a substitute, and it puts the one genuinely differentiated asset — the
production-derived governance model — behind the paywall where it belongs.

This is a recommendation, not a decision. The owner sets price.

---

## Verification performed for this report

| Claim | How it was checked |
|---|---|
| Risk tiers and escalators match production | Read `control-plane/app/governance.py` directly |
| Calculator arithmetic and disclaimer hold | `pytest tests/test_automation_roi.py` → 19 passed |
| 4 of 5 catalog links are live Stripe URLs | Parsed `data/store/catalog.json` |
| 8 offer pages are in the sitemap | `grep` of `sitemap.xml` |
| Offer pages convert via `mailto:` | Extracted `href`/`action` from the offer HTML |
| No placeholder `REPLACE_*` remains in offer pages | `grep` — survives only in `offers/README.md` |

**Not verified:** demand, willingness to pay, competitor pricing, the `book.stripe.com`
endpoint, and whether any of the pricing options above would convert. Those are marked
`NOT VERIFIED` and are not upgraded because the result looks probable.
