# ClearGlass Inc. — IP Protection Notice & Trade Secret Register

> **THIS IS GENERAL GUIDANCE; CONSULT LICENSED COUNSEL FOR YOUR JURISDICTION.**
>
> Effective Date: 2026-05-08
> Maintained by: ClearGlass Inc. Legal / IP Committee
> Review cycle: Quarterly (next review: 2026-08-01)

---

## 1. Risk Assessment

### 1.1 Copyright

| Asset Category | Status | Human-Authorship Evidence | Risk Level |
|---|---|---|---|
| Artemis AI platform blueprints (`docs/`, `*.md`) | Publicly hosted | Author commits in git log; human editorial decisions documented | **MEDIUM** — AI-assisted drafts without clear human-authorship documentation risk copyright voidability under 2026 case law |
| Python automation bots (`bots/`, `scripts/`) | Publicly hosted | Human-authored with AI pair-programming | **MEDIUM** — human authorship defensible but must be documented |
| HTML/CSS front-end pages | Publicly hosted | Human design decisions | **LOW–MEDIUM** |
| System prompts (`prompts/`) | Publicly hosted | Human-authored prompt engineering | **HIGH** — prompt copyright is unsettled; trade secret protection was the primary layer and it is compromised by public exposure |
| Downloadable scripts (`downloads/*.ps1`) | Publicly downloadable | Human-authored | **HIGH** — binaries freely downloadable; no licence wrapper |
| Legal document templates (`legal/`) | Publicly hosted | Human lawyer drafting | **MEDIUM** — template copyright may vest; ensure origination is documented |

**2026 copyright landscape note:** Post-*Thaler v. Vidal* and subsequent US Copyright Office guidance (Circular 65, updated 2026), AI-generated output without sufficient human creative control is uncopyrightable. All Artemis documents and bot code must have contemporaneous evidence of human editorial contribution (e.g., commit messages, design-decision logs, prompt revision history).

### 1.2 Trade Secrets

**CRITICAL — IMMEDIATE ACTION REQUIRED:**

The following materials are designated trade secrets but are currently exposed in a **public** GitHub repository. Public disclosure presumptively destroys trade-secret protection under the UTSA, DTSA, and Canadian equivalent statutes unless remediated.

| Asset | Location | Exposure Status | Remediation Priority |
|---|---|---|---|
| Artemis CEO Bot system prompt | `prompts/system_prompt.md` | **PUBLICLY EXPOSED** | P0 |
| Artemis Dashboard Agent prompt | `prompts/dashboard_agent_prompt.md` | **PUBLICLY EXPOSED** | P0 |
| StegoForge self-improving architecture | `scripts/stegoforge_self_improving_system.py` | **PUBLICLY EXPOSED** | P1 |
| ATT&CK intelligence bot logic | `scripts/artemis_attack_intel_bot.py` | **PUBLICLY EXPOSED** | P1 |
| Artemis platform architecture blueprints | `docs/clearglassinc_artemis_*.md` | **PUBLICLY EXPOSED** | P1 |
| Financial automation plan | `docs/clearglassinc_artemis_finance_*.md` | **PUBLICLY EXPOSED** | P1 |
| Revenue engine configuration | `revenue-engine.html` | **PUBLICLY EXPOSED** | P2 |
| Investor materials | `investors/` | **PUBLICLY EXPOSED** | P1 |

### 1.3 Licensing & Supply-Chain

| Risk | Details |
|---|---|
| No LICENSE file (prior to this PR) | Repository lacked any explicit licence; downstream users could claim implied rights |
| Unpinned GitHub Actions | `actions/checkout@v4`, `github/codeql-action@v3` use mutable version tags, not SHA pins — supply-chain attack surface |
| `requirements.txt` dependencies | Not SHA/hash-pinned; `pip install --require-hashes` not enforced |
| Terraform state | `infra/main.tf` present; `.terraform/` and `*.tfstate` must never be committed |
| Third-party AI tools (GitHub Copilot) | Without explicit `# GitHub Copilot: off` annotations on proprietary files, Copilot telemetry may ingest source code |

---

## 2. Protection Strategy

### 2.1 Copyright

1. **Document human authorship for every commit.** PR descriptions must state the human author's specific creative contributions where AI tooling assisted.
2. **Maintain a `HUMAN_AUTHORSHIP_LOG.md`** (private repo) recording: which sections of each blueprint were human-drafted, which were AI-suggested and then edited, and the decision rationale.
3. **Copyright notices** have been added to all Python source files (2026-05-08). HTML files should carry `<!-- Copyright (c) 2024-2026 ClearGlass Inc. -->` in `<head>`.
4. **Register key works** with the US Copyright Office (Form TX for software, Form VA for web design). Canadian registration optional but recommended for domestic enforcement.

### 2.2 Trade Secrets

1. **Immediate triage (P0):** Evaluate whether `prompts/system_prompt.md` and `prompts/dashboard_agent_prompt.md` must remain public for operational reasons. If not, move them to a **private repository** and purge from public git history using `git filter-repo`.
2. **Private repo split:** Create `ClearGlassInc/artemis-internal` (private) for:
   - All system prompts and prompt chains
   - StegoForge full implementation
   - Detailed financial/revenue configuration
   - Investor materials
3. **NDAs:** Ensure all contractors, employees, and early investors have signed the `legal/mutual_nda_template_ontario.md` NDA **before** receiving access to any internal repository.
4. **Access controls:** Use GitHub team permissions. Contributors should have minimum necessary access.
5. **Maintain secrecy:** Document all access grants in an internal access log.

### 2.3 AI/ML Model Output Protection

Under 2026 guidance:
- **Prompts as trade secrets** (not copyright): The structure, chaining logic, and domain-specific tuning of Artemis prompts are protectable as trade secrets if kept confidential, documented, and access-controlled. Public exposure has destroyed this protection for current prompts — rotate and replace them in a private repo.
- **AI-generated code:** Treat as work-made-for-hire with careful human-authorship documentation. Avoid claiming copyright in purely AI-generated sections without evidence of human creative selection/arrangement.

### 2.4 Patent Strategy

Evaluate patent filing for:
- StegoForge self-improving AI orchestration methodology (process patent)
- Artemis multi-agent feedback loop architecture (if novel and non-obvious)
- **Filing deadline:** 1 year from first public disclosure (US provisional); the public blueprints in this repository may have started this clock.

---

## 3. GitHub Recommendations

### 3.1 Branch Protection (apply to `main` immediately)

```
Settings → Branches → main:
  ✓ Require pull request reviews (min. 1 — org owner)
  ✓ Require status checks: ip-protection-scan / secret-scan
  ✓ Require status checks: ip-protection-scan / copyright-headers
  ✓ Require status checks: ip-protection-scan / license-check
  ✓ Do not allow bypassing the above settings
  ✓ Restrict pushes to org owner
```

### 3.2 Files Added by This PR

| File | Purpose |
|---|---|
| `LICENSE` | Proprietary all-rights-reserved licence; clarifies no downstream use permitted |
| `.github/CODEOWNERS` | All paths owned by `@ClearGlassInc`; required review on every PR |
| `.github/workflows/ip-protection-scan.yml` | Automated copyright, secret, and supply-chain scans on every push/PR |
| `.gitignore` additions | Blocks `.env`, credentials, Terraform state, private prompt drafts from accidental commit |
| Copyright headers | Added to all 15 Python source files |

### 3.3 Copilot Settings

Add `.github/copilot-instructions.md` with:
```
# GitHub Copilot Instructions
Do not suggest completions that reproduce proprietary ClearGlass Inc. source code.
Do not suggest completions based on files in /prompts/, /docs/, /investors/.
```

Set repository-level Copilot telemetry to "disabled" under:
`Settings → Code security and analysis → GitHub Copilot → Content exclusions`

Exclude paths: `prompts/`, `docs/`, `investors/`, `bots/`, `scripts/`

### 3.4 Secret Scanning

Enable under `Settings → Security → Secret scanning`:
- ✓ Secret scanning alerts
- ✓ Push protection (blocks commits containing detected secrets)
- ✓ Validity checks

### 3.5 Dependency Review

Add to workflow triggers:
```yaml
- uses: actions/dependency-review-action@v4
  with:
    fail-on-severity: high
```

---

## 4. Automation Suggestions

### 4.1 Running (as of this PR)

| Workflow | Trigger | IP Relevance |
|---|---|---|
| `ip-protection-scan.yml` | push/PR/weekly | Copyright headers, secret scan, licence check, supply-chain audit |
| `codeql.yml` | push/PR/weekly | Static analysis catches IP-sensitive data flows |

### 4.2 Recommended Additions

1. **`git-history-audit.yml`** — Weekly scan of full git history with `trufflehog` for any historically committed secrets (historical exposure ≠ current-file exposure).
2. **`dependency-pin-check.yml`** — Enforce `pip install --require-hashes` and SHA-pinned Actions.
3. **`copilot-content-exclusion-check.yml`** — Verify Copilot exclusions are in place via GitHub API.
4. **`ip-report.yml`** — Monthly auto-generated IP status report filed as a GitHub issue.

---

## 5. Action Checklist

### Immediate (within 48 hours)

- [ ] **P0-1:** Move `prompts/system_prompt.md` and `prompts/dashboard_agent_prompt.md` to a private repository and purge from public git history (`git filter-repo --path prompts/ --invert-paths`)
- [ ] **P0-2:** Rotate / replace all system prompts that were exposed (treat exposed prompts as compromised)
- [ ] **P0-3:** Enable GitHub Secret Scanning + Push Protection on this repository
- [ ] **P0-4:** Enable branch protection on `main` requiring IP scan status checks

### Short-term (within 1 week)

- [ ] **P1-1:** Move investor materials (`investors/`) to a private repository
- [ ] **P1-2:** Evaluate which `docs/clearglassinc_artemis_*.md` blueprints can remain public vs. must move private
- [ ] **P1-3:** Ensure all contractors/employees have signed NDAs (use `legal/mutual_nda_template_ontario.md`)
- [ ] **P1-4:** File US Provisional Patent Application for StegoForge methodology (1-year clock may be running)
- [ ] **P1-5:** Add `<!-- Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved. -->` to all HTML files
- [ ] **P1-6:** Pin GitHub Actions to SHA digests in all workflows

### Medium-term (within 30 days)

- [ ] **P2-1:** Register key software works with the US Copyright Office
- [ ] **P2-2:** Implement `HUMAN_AUTHORSHIP_LOG.md` discipline for all AI-assisted documents
- [ ] **P2-3:** Configure GitHub Copilot content exclusions for sensitive paths
- [ ] **P2-4:** Add `trufflehog` historical-scan workflow
- [ ] **P2-5:** Enforce `pip install --require-hashes` in CI
- [ ] **P2-6:** Add Terraform state to remote backend (not local files in repo); confirm `.tfstate` never committed
- [ ] **P2-7:** Create formal IP inventory spreadsheet with first-creation dates, authors, and classification levels

### Ongoing

- [ ] Quarterly IP review meeting with counsel
- [ ] Annual copyright registration renewal review
- [ ] IP clause in every new contractor/employee agreement
- [ ] Access-log review for private repositories (quarterly)

---

*This document is itself a trade secret of ClearGlass Inc. and is subject to the terms of the ClearGlass Inc. proprietary licence. Do not distribute outside the organisation without written authorisation.*

*This is general guidance; consult licensed counsel for your jurisdiction.*
