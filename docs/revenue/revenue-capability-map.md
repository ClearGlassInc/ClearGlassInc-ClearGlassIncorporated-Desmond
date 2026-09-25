# Revenue Capability Map

**As of 2026-09-25, `main` at `5b36840`.** This covers only capabilities with
code or files behind them. Labels follow [`revenue-baseline.md`](revenue-baseline.md):
VERIFIED, CARRIED, INFERENCE, ASSUMPTION, UNKNOWN.

## Which repository

34 ClearGlass-related repositories are visible to this account, across
`ClearGlassInc`, `ClearGlasslabs` and `ClearGlassIncorp` (repository list,
2026-09-25). Only one holds the production domain:

| Repository | Visibility | Last push | Production evidence | Decision |
|---|---|---|---|---|
| `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond` | public | 2026-09-25 | `CNAME` = `www.clearglassinc.com`; Pages "deploy from branch" on `main`; Pages run #177 deployed this repository's `main` (CARRIED, `AUDIT-2026-09-23.md`); all revenue code (`control-plane/`, Payment Links, offers) | **Production commercial system** |
| `ClearGlasslabs/ClearGlassInc.` | public | 2026-09-24 | Not inspected: outside this session's access scope. GitHub binds a custom domain to one Pages site at a time, so it cannot also serve `www.clearglassinc.com` | Not production |
| 32 others (`Opal-Koboi`, `ClearCast`, `clearglass-ai-proxy`, `Gaurdian`, forks, …) | mixed | 2026-07-06 to 2026-09-25 | Not inspected, same reason | Not production |

Trust note: several public forks under ClearGlass organizations carry names a
cautious buyer may read badly next to a security offer: `SocialPwned`,
`freedatabreaches`, `EmailAddressExtractor`, `PwnedPasswordsDownloader`. Owner
decision **D6** in [`revenue-decisions.md`](revenue-decisions.md).

## Scores

`COMMERCIAL SCORE = buyer clarity + problem urgency + existing implementation +
delivery readiness + trust/evidence + payment readiness − development required −
delivery risk`. Each factor is 0 to 5. Scores are this map's judgement of the
evidence cited in each row.

| Capability | Clar. | Urg. | Impl. | Ready | Trust | Pay | −Dev | −Risk | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| Security Quick-Audit, CAD 249 | 4 | 2 | 3 | 3 | 2 | 3 | 1 | 2 | **14** |
| Rapid Website & Deployment Audit, CAD 125 | 3 | 4 | 2 | 3 | 2 | 2 | 1 | 3 | **12** |
| 90-Minute Cyber Risk Audit, CAD 297 | 3 | 2 | 2 | 2 | 2 | 3 | 1 | 2 | **11** |
| Governed AI Automation Operating Kit (digital) | 2 | 1 | 4 | 3 | 2 | 1 | 2 | 1 | **10** |
| M365 + Windows Hardening Sprint, from CAD 2,500 | 4 | 2 | 2 | 2 | 1 | 2 | 1 | 3 | **9** |
| Guardian Command Nexus Blueprint, CAD 199 | 1 | 1 | 2 | 1 | 1 | 3 | 2 | 1 | **6** |
| CashPulse invoice-dunning pilot (n8n) | 3 | 3 | 2 | 1 | 1 | 1 | 3 | 3 | **5** |
| QICS quantum-readiness scoring | 2 | 1 | 3 | 1 | 1 | 0 | 3 | 2 | **3** |
| Managed Monitoring, from CAD 600/month | 3 | 2 | 1 | 0 | 1 | 2 | 4 | 4 | **1** (reject) |

PHIPA Readiness (from CAD 3,000) and Critical Minerals Compliance (CAD 1,499)
are not scored. They are regulatory advice without verified delivery capacity.

## Evidence per capability

| Capability | Buyer and problem | Deliverable and time | Current implementation (evidence) | Missing work | Commercial risk |
|---|---|---|---|---|---|
| **Security Quick-Audit** | Owner-run professional offices (accounting, law, property management) that cannot say whether their domain can be spoofed or what they expose | Top-10 risk-ranked findings report, 3 business days, read-only, written authorization (`offers/security-quick-audit.html`) | `tools/Invoke-CGSecurityAudit.ps1` builds a branded HTML report and has an authorization gate (not run in this environment: no PowerShell). `operations/email/verify_email_dns.py` checks SPF, DKIM and DMARC (tested). `scripts/cert_bot.py` checks TLS expiry (tested). Payment: live Payment Link `…Ni03` and Interac e-Transfer | Run the collector once on an owned machine to produce the internal sample report. The page promises an M365/Entra review that has no tooling here, so do it by hand (read-only) or drop it (**D10**) | Scope creep into free remediation |
| **Rapid Website & Deployment Audit** | Founders and creators with a broken site, form or deployment | Root-cause report and fix specification (`docs/CLEARGLASS-24H-RESCUE-SALES-KIT.md`: intake, statement of work and delivery-report templates) | Manual expertise. `site_reliability_audit.py` and `workflow_doctor.py` check this repository only (INFERENCE: they take no target argument) | No payment link for CAD 125 | A "24-hour" promise across unknown stacks. It reaches a different buyer from the lead list |
| **90-Minute Cyber Risk Audit** | Same buyer as the Quick-Audit | 90-minute session and a findings summary | Live Stripe Price and Payment Link `…Ni00`; control-plane SKU `risk-audit-90` | No delivery runbook | Duplicates the Quick-Audit. Two entry offers at CAD 249 and 297 undercut each other (**D2**) |
| **Automation Kit** | Small teams planning automation | 21 registered assets: 8 guides, 4 templates, a roadmap, a calculator | VERIFIED 2026-09-25: 8 of 8 tests pass; validator PASS with 0 findings (`product/automation-kit/validation/VALIDATION_REPORT.md`) | The whole kit is free in this public repository (**D7**). No price and no checkout | Selling content that is already free |
| **Hardening Sprint** | The same offices, after a Quick-Audit shows gaps | Fixed-scope M365 and Windows hardening | `Invoke-CGSecurityAudit.ps1` names the Sprint as its second use. The work itself is manual configuration | Statement of work per client; professional liability cover (ASSUMPTION: not checked) | Changes to client systems |
| **Guardian Blueprint** | Unclear | HTML blueprint by email within 1 business day | Free summary at `docs/guardian_command_nexus_spec.html`. The paid file was not located | The paid file | No identifiable buyer problem |
| **CashPulse** | SMBs with overdue invoices | n8n dunning and lead-capture workflows | Exports in `deployment/cashpulse/` only | n8n, Supabase, Stripe, QuickBooks and Twilio set up per client | Touches client money and customer communications |
| **QICS** | Organizations planning post-quantum migration | Exposure rating from a cryptographic inventory | `qics/`, 17 of 17 tests pass (VERIFIED 2026-09-25). It needs a JSON inventory as input | Inventory discovery; a report format | The buyer doesn't have the input it needs |

## Ladder chosen from the scores

| Rung | Offer | Why |
|---|---|---|
| **Primary** | Security Quick-Audit, CAD 249 | Highest score; delivery tooling in the repository; a live payment link, plus e-Transfer, which works without Stripe; a named buyer list of 10 |
| **Core / upsell** | Hardening Sprint | The natural next purchase for the same buyer once the report shows gaps. It ranks 5th on its own because a cold CAD 2,500 ask has no trust behind it, so it is never the first contact |
| **Implementation / retainer** | None yet | No recurring delivery exists. Business Protection (CAD 100/month and 1,000/year) and Managed Monitoring stay unpromoted until a Sprint customer needs ongoing work |
| Parallel entry, different buyer | Rapid Website & Deployment Audit, CAD 125 | Second highest score, but it reaches founders through communities, not the offices on the lead list. Run it only if the Quick-Audit channel stalls |
