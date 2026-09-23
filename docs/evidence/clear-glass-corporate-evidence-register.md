# ClearGlass Corporate Evidence Register

**Repository:** `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond` @ `9279b2f`  
**Retrieved:** 2026-09-17  
**Method:** static audit of committed repository content only.

> **No external verification was performed.** No Ontario Business Registry, CRA, PSPC, FedRAMP, SAM.gov or CCCS lookup was carried out. Every status below describes *what the repository can prove about itself* — nothing more.

## Bottom line

The repository contains **no authoritative corporate, tax, certification, procurement or contract record of any kind.** The only PDFs present are a Coursera course certificate, a domain-ownership letter, a Cloudflare domain certificate, and a planning kit. Several public pages nonetheless present unverified status as fact — one of them is contradicted by another file in the same repository.

## Register

| ID | Claim | Status | Supporting record found | Repository locations | Required action |
|---|---|---|---|---|---|
| CG-ENT-001 | ClearGlass Inc. is incorporated in Ontario | **NOT VERIFIED** | index.html assurance strip states "Incorporated in Ontario, Canada". No Certificate of Incorporation, OCN or Ontario Business Registry record exists in the repository. | `index.html`, `operations/ontario-incorporation-handoff.html` | Obtain the Ontario Certificate of Incorporation and Business Registry profile; until then remove or qualify the homepage assurance badge. |
| CG-ENT-002 | Ontario Corporation Number (OCN) | **NOT VERIFIED** | No OCN value appears anywhere. The term occurs only in a handoff workflow describing how to obtain one. | `operations/ontario-incorporation-handoff.html`, `blog/clearglassinc-0-to-1m-corporate-execution-plan.html` | Record the OCN from the Ontario Business Registry once issued. |
| CG-ENT-003 | Certificate of Incorporation held | **NOT VERIFIED** | No certificate artifact in the repository. PDFs present are a Coursera course certificate, a domain ownership letter, a Cloudflare domain certificate and the Institute founding kit. | `ClearGlass-Institute-Founding-Kit.md`, `legal/articles.html` | Store the issued certificate in a controlled evidence folder and reference it here. |
| CG-ENT-004 | Registered office address | **NOT VERIFIED** | 'registered office' appears only in templates and planning text, never as a filed address tied to a corporation number. | `ClearGlass-Institute-Founding-Kit.md` | Record the registered office as filed. |
| CG-ENT-005 | Directors and officers of record | **NOT VERIFIED** | Only unexecuted director-consent templates exist. | `ClearGlass-Institute-Founding-Kit.md` | Record directors from the filed Initial Return. |
| CG-NP-001 | ClearGlass Institute is an ONCA not-for-profit corporation | **NOT VERIFIED** | Founding kit describes it as a "Proposed ONCA Corp" and directors consent "upon incorporation" — pre-incorporation planning. | `ClearGlass-Institute-Founding-Kit.md` | Obtain the ONCA Certificate of Incorporation before any nonprofit status is stated publicly. |
| CG-NP-002 | ClearGlass Institute is a registered charity | **CORRECTLY DISCLAIMED** | The kit states: "It is not a registered charity with the Canada Revenue Agency and cannot issue official donation receipts for income tax purposes at this time." | `ClearGlass-Institute-Founding-Kit.md` | No action. Keep this disclaimer wherever donations are discussed. |
| CG-TAX-001 | CRA Business Number (BN) | **NOT VERIFIED** | Appears only as a future task: "Apply for the CRA Business Number, register for GST/HST". | `operations/ontario-incorporation-handoff.html`, `operations/procurement-readiness.html` | Record BN issuance privately; do not publish the number itself. |
| CG-TAX-002 | GST/HST registration | **NOT VERIFIED** | Referenced as a prerequisite still to be completed for supplier registration. | `operations/procurement-readiness.html` | Complete registration before invoicing tax. |
| CG-CERT-001 | FedRAMP authorization | **NOT VERIFIED** | government.html shows badges "FedRAMP READY" and "FedRAMP Authorization"; the body text says only "aligned to FedRAMP Moderate baselines". No package ID, authorization status or sponsoring agency. | `government.html`, `index.html` | Remove the authorization/ready badges or replace with 'designed against FedRAMP Moderate baselines (not authorized)'. |
| CG-CERT-002 | CMMC Level 2 certification | **NOT VERIFIED** | Badge reads "CMMC LEVEL 2"; body says "practices implemented". No C3PAO, assessment record or SPRS score. | `government.html`, `index.html` | Qualify as 'CMMC L2 practices implemented; not assessed or certified'. |
| CG-CERT-003 | SOC 2 Type II | **NOT VERIFIED** | Badge reads "SOC 2 TYPE II"; body says "SOC 2 Type II Readiness". No report, auditor, period or scope. | `government.html` | Display as 'SOC 2 Type II readiness' only, with no badge implying a completed report. |
| CG-CERT-004 | CCCS alignment (ITSG-33) | **SELF-ASSESSED — NOT INDEPENDENTLY ATTESTED** | government.html claims platforms "aligned to CCCS Security Controls Catalogue (ITSG-33)". Self-description, no CCCS assessment. | `government.html`, `artemis-iv.html` | Keep the word 'aligned'; never imply CCCS assessment or endorsement. |
| CG-CERT-005 | ITAR / DDTC registration | **NOT VERIFIED** | ITAR is referenced widely in generated planning documents; no DDTC registration code or record exists. | `government.html` | Remove ITAR from capability badges unless DDTC-registered. |
| CG-PROC-001 | Listed under PSPC ProServices Supply Arrangement, SIN 3.3 | **CONTRADICTED** | government.html states: "ProServices - SIN 3.3 (Cybersecurity) Listed under PSPC ProServices Supply Arrangement - SIN 3.3 IT Security". The same repository states federal supplier registrations are still outstanding. | `government.html`, `operations/procurement-readiness.html`, `operations/federal-supplier-handoff.html` | HIGHEST PRIORITY: replace the affirmative listing statement with 'Procurement status: NOT VERIFIED - supply arrangement not held.' |
| CG-PROC-002 | CanadaBuys / SRI supplier registration | **NOT VERIFIED** | Registration is described as an action still to be performed, requiring founder authentication and an Integrity Declaration. | `government.html`, `operations/federal-supplier-handoff.html` | State as 'registration in progress' or omit. |
| CG-PROC-003 | SAM.gov registration / CAGE / UEI | **NOT VERIFIED** | Referenced as a pathway; no UEI, CAGE code or SAM record. | `government.html` | Omit until a UEI/CAGE is issued. |
| CG-CON-001 | Government contract or award held | **NO EVIDENCE** | No award notice, solicitation number, contract number, standing offer or task authorization exists anywhere in the repository. | `government.html` | Do not state or imply any government customer. |
| CG-OPS-001 | Production deployments with customers | **NOT VERIFIED** | 'production deployment' appears in specs, plans and CI documentation. No customer, contract or authenticated production evidence. | `AGENTS.md`, `BURLINGTON_TECH_IMPLEMENTATION_PLAN.md` | Classify products as code/prototype unless a customer record exists. |
| CG-OPS-002 | Penetration test performed | **NOT VERIFIED** | Mentioned in policy and IP-assignment language, not as a delivered report. | `access-control-audit.md`, `legal/ip-assignment.html` | Do not claim testing without a report. |
| CG-OPS-003 | 24-Hour Deployment Rescue commercial engagement | **NOT VERIFIED** | Only an offer/sales kit exists: "Offer Name: ClearGlass 24-Hour Website & GitHub Deployment Rescue", with outreach email templates. | `docs/CLEARGLASS-24H-RESCUE-SALES-KIT.md`, `RAPID-REVENUE-OPS-Offer-Kit.md` | State as an offered service, never as completed engagements. |
| CG-ID-001 | Founder/director identity linkage for Desmond Otieno Odhiambo | **NOT VERIFIED** | The name appears in ~119 repository files as author/founder attribution. No authoritative corporate director record links this identity to a registered corporation. | `index.html`, `data/corporate-identity.json` | Establish linkage only from the Ontario director record once incorporated. |
| CG-NET-001 | clearglass-network-overdrive deployment-rescue product | **OUT OF SCOPE — NOT AUDITED** | No such directory exists in this repository. ClearGlassInc/clearglass-network-overdrive is a separate repository (public, last pushed 2026-08-10). | — | Audit separately before describing it as a product or service. |

## Limitations recorded per claim

**CG-ENT-001** — ClearGlass Inc. is incorporated in Ontario

- Contradicted in-repo: operations/ontario-incorporation-handoff.html instructs the founder to 'Capture the resulting Ontario Corporation Number (OCN) and the issued Certificate of Incorporation' (future tense) and not to sign contracts in the corporate name 'until the Ontario Certificate of Incorporation has been issued'.

**CG-ENT-002** — Ontario Corporation Number (OCN)

- An incorporation workflow is a plan, not an incorporation record.

**CG-ENT-003** — Certificate of Incorporation held

- No corporate registry document of any kind is committed.

**CG-ENT-004** — Registered office address

- Template language only.

**CG-ENT-005** — Directors and officers of record

- Template contains placeholder '[Full Legal Name]'.

**CG-NP-001** — ClearGlass Institute is an ONCA not-for-profit corporation

- A separate repository ClearGlassInc/ClearGlass-Institute- exists but was not audited here.

**CG-NP-002** — ClearGlass Institute is a registered charity

- This disclaimer is accurate and should be preserved verbatim.

**CG-TAX-001** — CRA Business Number (BN)

- No BN value is present, and none should be published once obtained without a confidentiality review.

**CG-TAX-002** — GST/HST registration

- Listed under 'Requires PBN, GST/HST number' — a requirement, not a holding.

**CG-CERT-001** — FedRAMP authorization

- Alignment to a baseline is not an authorization. 'FedRAMP Ready' is itself a designation issued through the FedRAMP PMO and is not evidenced.

**CG-CERT-002** — CMMC Level 2 certification

- Implementing practices is not certification.

**CG-CERT-003** — SOC 2 Type II

- Readiness is not an audited report.

**CG-CERT-004** — CCCS alignment (ITSG-33)

- CCCS did not assess or endorse anything evidenced here.

**CG-CERT-005** — ITAR / DDTC registration

- Mentions are aspirational or contextual.

**CG-PROC-001** — Listed under PSPC ProServices Supply Arrangement, SIN 3.3

- Direct internal contradiction: operations/procurement-readiness.html lists 'PENDING - FOUNDER Federal supplier registrations - SRI, SAP Ariba, Integrity Declaration', and federal-supplier-handoff.html is titled 'Submit federal supplier registrations' with status 'PENDING - CREDENTIALS'.
- A ProServices listing would require a qualified supply arrangement holder record; none is evidenced.

**CG-PROC-002** — CanadaBuys / SRI supplier registration

- Explicitly PENDING in the handoff.

**CG-PROC-003** — SAM.gov registration / CAGE / UEI

- No identifiers of any kind.

**CG-CON-001** — Government contract or award held

- 'procurement-ready' and 'structured for rapid award' are forward-looking, not awards.

**CG-OPS-001** — Production deployments with customers

- Sophisticated source code is not evidence of a production customer deployment.

**CG-OPS-002** — Penetration test performed

- No scope, tester or report.

**CG-OPS-003** — 24-Hour Deployment Rescue commercial engagement

- Capability and offer are documented; no invoice, contract, customer letter or engagement record.
- The kit does carry an accurate non-affiliation disclaimer, which should be preserved.

**CG-ID-001** — Founder/director identity linkage for Desmond Otieno Odhiambo

- Repository self-attribution is not an authoritative identity record.
- Name similarity must not be used to merge identities with other individuals.

**CG-NET-001** — clearglass-network-overdrive deployment-rescue product

- Not audited here; no conclusion is drawn about its code or any engagement.
