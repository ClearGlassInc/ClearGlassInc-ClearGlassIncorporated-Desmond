# Revenue Decisions

Owner decisions that stand between today and the first verified payment, in
priority order. Each gives the options, a recommendation and what waiting
costs. **Status** changes only when the owner decides.

| ID | Decision | Why it blocks revenue | Options | Recommendation | Cost of waiting | Status |
|---|---|---|---|---|---|---|
| **D1** | Confirm Stripe can charge | Nine live Payment Links, including the primary offer's `…Ni03`, fail at checkout if `charges_enabled` is false (last known state, 2026-08-05) | Complete the 5 overdue onboarding items / take e-Transfer only for now | Check the Stripe Dashboard today. Until it reads `true`, invoice by e-Transfer, which the Quick-Audit page already offers | Any buyer who clicks "Buy" hits a failed checkout | OPEN |
| **D2** | One entry offer and price | CAD 125, 199, 249 and 297 are all public entry prices | Quick-Audit 249 / Risk Audit 297 / Rapid Audit 125 | Quick-Audit at CAD 249: highest capability score and existing tooling. Stop promoting the 297 audit as a separate entry | A buyer who sees four entry prices hesitates | OPEN |
| **D3** | Refund, cancellation and assessment-authorization terms | No paid page carries them. Stripe onboarding asks for a refund policy (ASSUMPTION: current Stripe requirements not verified here) | Adapt `legal/master_services_agreement_template_ontario.md` / get a lawyer's review | Short plain-language terms plus a one-page authorization letter, reviewed before first use | Chargeback exposure, and an authorization gap on security work | OPEN |
| **D4** | Mailing address in commercial email (CASL) | CASL requires a valid mailing address in every commercial email | Registered office address / PO box or virtual mailbox | PO box if the registered address is a home. The drafts carry the registered address until this is decided | No compliant cold email can be sent | OPEN |
| **D5** | Sending domain for outreach | Pitching email security from a personal iCloud address undercuts the pitch | `@clearglassinc.com` mailbox / personal address | Make the domain mailbox work, and send from it | Lower reply rate | OPEN |
| **D6** | Public-repository hygiene | Buyers and search engines can read everything here | See the list below | Do all of it; each item is under an hour | Trust damage that no page copy can repair | OPEN |
| **D7** | Automation Kit sale path | The kit is free in this public repository | Private repository plus a paid edition / give it away as a lead magnet | Use it as a free lead magnet with the booking link. Build a paid edition only after 3 Quick-Audit sales | Selling free content invites refunds | OPEN |
| **D8** | Merge the change that removes the exposed files | The executable and the confidential record stay live on the site until it merges | Merge / leave open | Merge | Continued exposure | OPEN |
| **D9** | Rename the Calendly event | "30 Minute Meeting" is generic | "Security Quick-Audit scoping call" / keep | Rename it; no other change needed | Minor | OPEN |
| **D10** | The M365 / Entra line in the Quick-Audit scope | No tooling in the repository covers it | Deliver it by hand, read-only / remove it from the page | Deliver by hand for the first 3 clients and time it | An unfulfilled line in a paid scope | OPEN |

## D6: public-repository hygiene, itemized

1. `internal/ontario-company-key-order.md` is marked "Do not publish" and holds
   billing, contact and payment details. It is removed from `main` in this
   change, but **it remains in public git history**. Removing it from history
   means rewriting `main` and asking GitHub Support to purge cached views. That
   is destructive, so it is not done here.
2. `offers/outreach/lead-list-oakville-burlington.csv` names 10 local firms with
   internal notes such as "likely no formal security review". Move the working
   copy somewhere private.
3. The 16:52 upload (`b1a72f4`) put personal and unrelated files on the public
   site: Coursera PDFs, a crossword PDF, analytics exports, notebooks and
   a zip archive. Keep only what belongs on a company website.
4. Public forks under ClearGlass organizations include `SocialPwned`,
   `freedatabreaches`, `EmailAddressExtractor` and `PwnedPasswordsDownloader`.
   Archive them, or make them private, before prospects search the brand.

## Engineering done this session, and why (owner rule 4A)

| Work | Why engineering was needed now | Revenue outcome it supports | Evidence |
|---|---|---|---|
| Removed the executable from the site | A 12 MB Windows binary (`updater.exe`, "Google Updater (x86)") served from a security firm's domain risks safe-browsing flags that would take every page and payment link down | Keeps the site able to sell | PE version info read without executing it |
| Removed the confidential record from the site | The file itself says "Do not publish" | Trust; personal data exposure | File header |
| Added the Calendly CTA to the Quick-Audit page | The primary offer had no way to book a call, only "email for a link" | Qualified → Meeting | Calendly event active (2026-09-24) |
| Recorded the kit validation run | Its report said NOT VERIFIED | Evidence before claims | 8 of 8 tests, validator PASS |

The commercial action this supports is sending drafts 1 to 5 of the private
outreach file on the next business day.
