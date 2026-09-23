# ClearGlass Claims Verification Matrix

**Repository:** `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond` @ `9279b2f`
**Retrieved:** 2026-09-17
**Scope:** committed repository content only.

> **No external verification was performed.** No Ontario Business Registry, CRA, PSPC/CanadaBuys, FedRAMP PMO, SAM.gov or CCCS lookup was carried out in this audit. A status of `NOT VERIFIED` means *the repository does not evidence it* — it is not a finding that the claim is false, except where marked `CONTRADICTED`.

---

## LEGAL ENTITY

| Item | Status | Basis |
|---|---|---|
| Legal name (`ClearGlass Inc.`) | **NOT VERIFIED** | Used throughout; no registry record |
| Ontario Corporation Number (OCN) | **NOT VERIFIED** | No value present; only a workflow describing how to obtain one |
| Incorporation date | **NOT VERIFIED** | Not stated anywhere |
| Corporation status | **NOT VERIFIED** | No registry profile |
| Registered office | **NOT VERIFIED** | Template language only |
| Directors / officers | **NOT VERIFIED** | Only unexecuted consent templates with `[Full Legal Name]` placeholders |

**Contradiction on record.** `index.html` presents "Incorporated in Ontario, Canada" as an assurance badge, while `operations/ontario-incorporation-handoff.html` instructs the founder to *"Capture the resulting Ontario Corporation Number (OCN) and the issued Certificate of Incorporation"* and warns that ClearGlass *"does not sign client contracts, vendor agreements, or banking documents in the corporate name until the Ontario Certificate of Incorporation has been issued."* The handoff is a pre-incorporation plan. **An incorporation plan is not an incorporation record.**

---

## NONPROFIT / CHARITY

| Item | Status | Basis |
|---|---|---|
| ONCA incorporation (ClearGlass Institute) | **NOT VERIFIED** | Founding kit describes a *"Proposed ONCA Corp"*; directors consent *"upon incorporation"* |
| ClearGlass Institute as a legal entity | **NOT VERIFIED** | Planning kit only (a separate repository `ClearGlassInc/ClearGlass-Institute-` exists and was **not** audited here) |
| CRA registered charity | **CORRECTLY DISCLAIMED** | The kit states it *"is not a registered charity with the Canada Revenue Agency and cannot issue official donation receipts."* |
| T3010 filing | **NOT APPLICABLE** | Follows from the above — no charity registration to file against |

The charity disclaimer is accurate and well-drafted. **Preserve it verbatim** anywhere donations, sponsorship or tax receipting are mentioned.

---

## TAX

| Item | Status | Basis |
|---|---|---|
| CRA Business Number | **NOT VERIFIED** | Appears as a future task: *"Apply for the CRA Business Number"* |
| GST/HST registration | **NOT VERIFIED** | Listed as a prerequisite (*"Requires PBN, GST/HST number"*), not a holding |

No BN or GST/HST value appears in the repository. When issued, record it in a controlled location — **do not publish the number itself.**

---

## CERTIFICATIONS

| Item | Status | What the page shows vs. what it evidences |
|---|---|---|
| FedRAMP | **NOT VERIFIED** | Badges read `FedRAMP READY` / `FedRAMP Authorization`; body says only *"aligned to FedRAMP Moderate baselines."* No package ID, authorization status or sponsoring agency. "FedRAMP Ready" is itself a PMO-issued designation and is not evidenced. |
| CMMC Level 2 | **NOT VERIFIED** | Badge reads `CMMC LEVEL 2`; body says *"practices implemented."* Implementing practices is not certification. |
| C3PAO assessment | **NOT VERIFIED** | No assessor, level or assessment record |
| SPRS score | **NOT VERIFIED** | Not present |
| SOC 2 Type II | **NOT VERIFIED** | Badge reads `SOC 2 TYPE II`; body says *"SOC 2 Type II Readiness."* No report, auditor, period or scope. |
| DDTC / ITAR | **NOT VERIFIED** | ITAR appears as a capability badge; no DDTC registration code |
| CCCS | **SELF-ASSESSED ALIGNMENT** | *"aligned to CCCS Security Controls Catalogue (ITSG-33)"* — a self-description. CCCS assessed nothing. |

**Pattern:** in each case the badge asserts a stronger status than the sentence beneath it. A reader scanning badges sees certification; only the body text reveals alignment or readiness. `index.html` handles this correctly — *"with federal control frameworks in mind, including FedRAMP, CMMC Level 2, CCCS"* — and is the model to follow.

---

## PROCUREMENT

| Item | Status | Basis |
|---|---|---|
| PSPC ProServices, SIN 3.3 | **CONTRADICTED** | See below |
| CanadaBuys / SRI registration | **NOT VERIFIED** | Explicitly `PENDING` in the handoff |
| PSPC Integrity Declaration | **NOT VERIFIED** | Described as still to be read and signed |
| Ontario / municipal rosters (MERX, Bonfire) | **NOT VERIFIED** | Described as a future mirroring step |
| SAM.gov / CAGE / UEI | **NOT VERIFIED** | No identifiers of any kind |

### The most serious finding

`government.html` states:

> *"ProServices — SIN 3.3 (Cybersecurity) · Listed under PSPC ProServices Supply Arrangement — SIN 3.3 IT Security"*

**"Listed under" is an affirmative assertion of qualified supplier status.** Two other files in the same repository say otherwise:

- `operations/procurement-readiness.html` — *"PENDING · FOUNDER — Federal supplier registrations — SRI, SAP Ariba, Integrity Declaration."*
- `operations/federal-supplier-handoff.html` — titled *"Submit federal supplier registrations,"* status *"PENDING · CREDENTIALS."*

A supplier cannot simultaneously be listed under a supply arrangement and have its supplier registration pending. This is an internal contradiction, and it is the claim with the greatest legal exposure: misrepresenting qualification under a federal supply arrangement is a procurement-integrity matter, not a marketing imprecision.

---

## CONTRACTS / AWARDS

**NO VERIFIED CONTRACT FOUND IN REPOSITORY EVIDENCE.**

No award notice, solicitation number, contract number, standing offer, task authorization or purchase order exists anywhere in the repository. The phrases *"procurement-ready for Canadian and US federal acquisition vehicles"* and *"structured for rapid award"* are forward-looking statements of intent and must not be read as awards. **No government customer may be stated or implied.**

---

## OPERATIONS

| Item | Status | Basis |
|---|---|---|
| Authenticated production URL | **NOT VERIFIED** | No authenticated production evidence |
| Runnable source | **PARTIALLY — not assessed per-product** | Repository holds substantial real source; per-product runnability was not individually established in this audit |
| Production deployment | **NOT VERIFIED** | *"production deployment"* appears in specs, plans and CI docs — not as a customer deployment record |
| Customer evidence | **NO EVIDENCE** | No invoice, contract, customer letter or reference |
| Penetration test | **NOT VERIFIED** | Referenced in policy/IP language; no scope, tester or report |
| Security assessment | **NOT VERIFIED** | No assessment record |

**Sophisticated source code is not evidence of a production customer deployment.** These must remain separate classifications.

### Deployment rescue

| Layer | Status |
|---|---|
| Code capability | Documented as an offer; `clearglass-network-overdrive` is a **separate repository** and was not audited here |
| Commercial service | **OFFERED** — sales kit, pricing and outreach templates exist |
| Verified customer engagement | **NOT VERIFIED** — no invoice, contract, customer letter or engagement record |

`RAPID-REVENUE-OPS-Offer-Kit.md` carries an accurate non-affiliation disclaimer (*"Not affiliated with Goldman Sachs, Stripe, PayPal, Etsy, GitHub, OpenAI"*). **Preserve it.**

---

## IDENTITY

| Item | Status | Basis |
|---|---|---|
| Founder (Desmond Otieno Odhiambo) | **NOT VERIFIED as a corporate-record linkage** | The name appears in ~119 files as author/founder attribution |
| Director of record | **NOT VERIFIED** | No corporation exists on the evidence available, so no director record can link to it |

Repository self-attribution is not an authoritative identity record. Identity linkage must come from the Ontario director record once incorporation is complete. **Name similarity must never be used to merge identities** — overlapping Desmond / Otieno / Odhiambo names belong to different people.

---

## Required corrective actions, in priority order

1. **`government.html` — ProServices/SIN 3.3.** Replace the affirmative listing with `Procurement status: NOT VERIFIED — supply arrangement not held.` This is the contradicted claim and the highest exposure.
2. **`government.html` — certification badges.** Make each badge match its own body text: readiness and alignment, never authorization or certification.
3. **`index.html` — "Incorporated in Ontario, Canada."** Remove or qualify until the certificate is issued.
4. **Create a controlled evidence folder** and file each authoritative record as it is obtained, updating this matrix and the register by ID.

Nothing in this audit should be deleted to resolve a finding. The original claim text is preserved in `clear-glass-corporate-evidence-register.md` so provenance survives the correction.
