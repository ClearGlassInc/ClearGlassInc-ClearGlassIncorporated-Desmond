# Governed AI Automation Operating Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an original, non-public ClearGlass digital business-automation planning and governance toolkit on an isolated branch, with deterministic calculator tests, provenance/IP controls, content-policy validation, and a reviewable validation report.

**Architecture:** Keep the MVP isolated under `product/automation-kit/` and a single product design document under `docs/products/`. Use Markdown/JSON for portable customer-facing planning assets and a small dependency-free Python calculator/validator where executable behavior is required. Do not modify the existing site, payment flow, deployment architecture, workflows, or production configuration.

**Tech Stack:** Markdown, JSON, Python 3 standard library, pytest where already available, existing repository validation tooling.

**Spec:** Owner-approved MVP design in the conversation; product design document created as part of Task 1.

## Global Constraints

- Internal planning, creation, and validation only; no publication, customer outreach, marketplace listing, checkout activation, payment processing, advertising spend, invoice creation, contract execution, account modification, or money movement.
- Preserve all existing ClearGlass functionality, Pages compatibility, CI, deployment paths, commerce safeguards, and visual identity.
- Only original ClearGlass-authored material or material with documented compatible licensing may be included.
- Do not copy marketplace titles, descriptions, images, instructions, file structures, workflows, branding, reviews, or customer content.
- Do not include customer data, credentials, tokens, keys, private-repository content, or confidential operating information.
- No guarantees of revenue, savings, ROI, compliance, security, performance, adoption, or business outcomes.
- No legal, tax, financial, compliance, security-certification, pentesting, or professional-regulated advice claims.
- Calculator outputs are estimates based on user-entered assumptions and are planning aids only.
- Evidence-safe vocabulary: use `PASS`, `FAIL`, and `NOT VERIFIED`; never claim verification without fresh evidence.
- Do not modify `main`; work only on `feat/governed-ai-automation-operating-kit`.

---

### Task 1: Establish the product specification and package boundary

**Files:**
- Create: `docs/products/governed-ai-automation-operating-kit.md`
- Create: `product/automation-kit/README.md`
- Create: `product/automation-kit/asset-register.json`

**Interfaces:**
- Produces the canonical product scope, allowed/prohibited language, package map, and provenance contract used by all later tasks.

- [ ] **Step 1: Write the product specification**

Create the canonical product document with the approved purpose, customer profiles, 12 approved components, scope statement, prohibited claims, originality/IP rules, release boundary, and validation requirements. Explicitly state that the artifact is internal/non-public until separately approved.

- [ ] **Step 2: Write the package README**

Document the package tree, intended use of each artifact, the calculator disclaimer, validation commands, and non-public release boundary. Do not add sales copy or marketplace metadata.

- [ ] **Step 3: Create the asset register**

Use a machine-readable schema with fields: `asset_id`, `path`, `title`, `origin`, `author`, `license_status`, `source_location`, `version`, `review_status`, `release_status`. New ClearGlass-authored assets must be marked as internally created with ownership/license review status explicit rather than implying legal certification.

- [ ] **Step 4: Verify package scope**

Run a repository search for the new paths and confirm no existing files were selected for modification.

---

### Task 2: Build the planning and governance templates

**Files:**
- Create: `product/automation-kit/content/automation-opportunity-assessment.md`
- Create: `product/automation-kit/content/workflow-inventory.md`
- Create: `product/automation-kit/content/automation-prioritization-matrix.md`
- Create: `product/automation-kit/content/automation-risk-tiering-framework.md`
- Create: `product/automation-kit/content/human-approval-gate-model.md`
- Create: `product/automation-kit/content/automation-governance-checklist.md`
- Create: `product/automation-kit/content/evidence-provenance-checklist.md`
- Create: `product/automation-kit/content/security-privacy-readiness-checklist.md`

**Interfaces:**
- Produces reusable, original Markdown templates that reference no customer-specific data and do not require external services.

- [ ] **Step 1: Define the opportunity assessment fields**

Include problem statement, current workflow, trigger, inputs/outputs, owner, stakeholders, repetitive effort, dependencies, risks, candidate automation, human decision points, evidence requirements, and implementation readiness.

- [ ] **Step 2: Define the workflow inventory schema**

Use a repeatable table covering workflow ID, owner, trigger, systems, data classification, steps, decision points, failure modes, manual effort, automation candidate, approval requirement, evidence location, and review date.

- [ ] **Step 3: Define prioritization and risk frameworks**

Provide transparent criteria rather than opaque scores. Separate value, effort, dependency, reversibility, data sensitivity, operational impact, and human oversight. State that prioritization is a planning aid, not a guarantee of outcome.

- [ ] **Step 4: Define approval, governance, provenance, and security checklists**

Require explicit owner approval, least privilege, data minimization, secrets exclusion, auditability, rollback/recovery planning, evidence retention, human escalation, and review checkpoints.

- [ ] **Step 5: Scan for prohibited claims and external-copy indicators**

Review each file for guarantee language, professional-advice claims, customer data, credentials, and marketplace-derived wording. Any uncertain provenance is marked `NOT VERIFIED` and excluded from release readiness.

---

### Task 3: Build the SOP and implementation roadmap assets

**Files:**
- Create: `product/automation-kit/templates/sop-template.md`
- Create: `product/automation-kit/templates/automation-change-record.md`
- Create: `product/automation-kit/templates/approval-record.md`
- Create: `product/automation-kit/templates/implementation-readiness-review.md`
- Create: `product/automation-kit/roadmap/30-60-90-day-automation-roadmap.md`
- Create: `product/automation-kit/examples/illustrative-workflows.md`

**Interfaces:**
- Provides implementation-ready documentation structures without implementing or executing customer automation.

- [ ] **Step 1: Create the SOP template**

Include purpose, scope, prerequisites, inputs, procedure, decision points, controls, exception handling, evidence, owner, reviewer, rollback, and change history.

- [ ] **Step 2: Create approval/change records**

Make approval explicit and append-only in concept: request, risk tier, affected systems, proposed change, approver, decision, timestamp, evidence reference, and rollback state.

- [ ] **Step 3: Create implementation-readiness review**

Cover technical prerequisites, identity/access, data handling, observability, testing, failure handling, human review, rollback, ownership, and evidence.

- [ ] **Step 4: Create the 30/60/90-day roadmap**

Organize discovery/baseline, controlled pilots, governance hardening, measurement, and review. Avoid promises about savings or business results.

- [ ] **Step 5: Create original illustrative workflows**

Include generic examples such as intake triage, document classification, reporting preparation, and approval routing. Explicitly mark them illustrative and non-client-specific; include no secrets, PII, copied workflows, or external proprietary material.

---

### Task 4: Implement the ROI/effort calculator with TDD

**Files:**
- Create: `product/automation-kit/calculators/automation_value.py`
- Create: `product/automation-kit/calculators/README.md`
- Create: `product/automation-kit/tests/test_automation_value.py`

**Interfaces:**
- `estimate_annual_hours_saved(hours_per_run: float, runs_per_week: float, automation_fraction: float) -> float`
- `estimate_annual_labor_value(hours_saved: float, hourly_cost: float) -> float`
- `estimate_net_annual_value(annual_labor_value: float, annual_automation_cost: float) -> float`
- `estimate_simple_payback_months(initial_cost: float, monthly_net_value: float) -> float | None`
- `calculate(inputs: dict[str, float]) -> dict[str, float | None]`

- [ ] **Step 1: Write failing tests**

Cover normal estimates, zero values, fractional automation, negative-input rejection, zero/negative monthly benefit producing `None` payback, and deterministic disclaimer presence in the public calculation result.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m pytest product/automation-kit/tests/test_automation_value.py -v`
Expected: FAIL because the calculator module does not yet exist.

- [ ] **Step 3: Implement the minimal calculator**

Use only the Python standard library. Reject non-finite or negative numeric inputs with `ValueError`. Keep formulas transparent and documented. Return no currency formatting; return numeric planning values plus the mandatory estimate-only notice.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the same pytest command and require zero failures.

- [ ] **Step 5: Add calculator usage documentation**

Document assumptions, formulas, units, and the mandatory notice: `Outputs are estimates based on user-entered assumptions. They are planning aids only and do not guarantee savings, financial results, return on investment, operational performance, or business outcomes.`

---

### Task 5: Add automated provenance and content-policy validation

**Files:**
- Create: `product/automation-kit/validation/validate_kit.py`
- Create: `product/automation-kit/tests/test_validate_kit.py`

**Interfaces:**
- `validate_asset_register(path: str) -> list[str]`
- `validate_text_policy(root: str) -> list[str]`
- `validate_required_notice(root: str) -> list[str]`
- `run_validation(root: str) -> dict[str, object]`

- [ ] **Step 1: Write failing tests**

Test that missing asset-register fields fail, a forbidden guarantee phrase fails, missing calculator notice fails, and a valid package returns no findings.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest product/automation-kit/tests/test_validate_kit.py -v`
Expected: FAIL because the validator does not yet exist.

- [ ] **Step 3: Implement the validator**

Scan only the product package. Validate register completeness, file existence, release-status consistency, mandatory notice, and a bounded set of explicitly prohibited claim patterns. Do not attempt to make legal determinations; flag text for review.

- [ ] **Step 4: Run tests and verify GREEN**

Run the focused validator tests and require zero failures.

- [ ] **Step 5: Run the validator against the full package**

Require an empty findings list for a validation-ready state. Any uncertain provenance or ambiguous policy hit must remain `NOT VERIFIED` rather than being auto-approved.

---

### Task 6: Generate the internal validation report

**Files:**
- Create: `product/automation-kit/validation/VALIDATION_REPORT.md`
- Create: `product/automation-kit/validation/VALIDATION_MANIFEST.json`

**Interfaces:**
- Records evidence from the calculator tests, validator tests, asset register, prohibited-content scan, and repository diff review.

- [ ] **Step 1: Capture exact test commands and results**

Record commands, exit codes, and counts from fresh execution. Do not insert guessed results.

- [ ] **Step 2: Record package inventory and provenance status**

List all product assets and their register statuses. Any unverified item must be explicitly marked `NOT VERIFIED`.

- [ ] **Step 3: Record release boundary**

State that no Etsy listing, Stripe object, checkout/payment activation, advertising, customer outreach, invoice, contract, or production deployment was performed.

- [ ] **Step 4: Validate the report itself**

Ensure it contains no fabricated metrics, sales claims, customer evidence, or release claims.

---

### Task 7: Final repository verification and reviewable handoff

**Files:**
- Modify only files created by Tasks 1–6.

**Interfaces:**
- Produces a clean, isolated feature branch suitable for human review; no merge or production mutation.

- [ ] **Step 1: Compare branch against main**

Run the repository comparison and confirm only the approved product/plan files changed.

- [ ] **Step 2: Run all focused tests**

Run: `python -m pytest product/automation-kit/tests -v`

- [ ] **Step 3: Run the package validator**

Run: `python product/automation-kit/validation/validate_kit.py`

- [ ] **Step 4: Search for secrets and prohibited artifacts**

Search the new package for credential/token patterns, customer identifiers, private URLs, and prohibited marketplace-copy indicators. Record exact findings.

- [ ] **Step 5: Review the diff**

Confirm no existing site, commerce, workflow, authentication, deployment, or payment files were modified.

- [ ] **Step 6: Commit the isolated implementation**

Use a descriptive commit such as `feat: add governed AI automation operating kit` only after all applicable verification gates pass.

- [ ] **Step 7: Stop before merge/publication**

Do not merge to `main`, publish the product, create an Etsy listing, create Stripe objects, activate checkout, process payments, contact customers, advertise, invoice, contract, or deploy production. Report the branch, commit, tests, validation status, and any `NOT VERIFIED` items.

---

## Self-review checklist

- Spec coverage: all 12 approved product components are represented across the product specification, templates, calculator, roadmap, examples, and validation package.
- IP controls: every asset is represented in `asset-register.json`; uncertain provenance is not release-approved.
- Safety controls: no guarantees, regulated professional advice, customer data, credentials, or autonomous high-impact actions are included.
- Financial boundary: calculator is a planning aid only; no transaction or payment integration is activated.
- Repository safety: isolated branch; no main merge; no existing application/deployment/payment behavior changed.
- Evidence: all status claims in the validation report must be tied to fresh command output or explicit `NOT VERIFIED` status.
