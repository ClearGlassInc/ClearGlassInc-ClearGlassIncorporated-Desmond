# Founder Credentials Register

Every material claim in the homepage founder section (`index.html#founder`),
linked to its evidence. This is the claim ledger `agent_army/AGENT_POLICY.md`
asks for, applied to the founder profile.

**Rule.** A licence or certification mark is published only when the section
also links to the issuer's public register, so a reader can check it.
`tests/test_founder_profile.py` enforces this for patent and trademark agents
and for the ISC2, PMI, EC-Council, ASCM and ISACA marks.

Last reviewed: 2026-10-01. The ISC2, PMI, EC-Council, ISACA and ASCM pages
below were found by web search that day. The USPTO and CPATA registers could
not be opened from the build environment (egress blocked). Nothing in this
file has been checked against a register.

## Published

| Claim on the page | Source | Check |
|---|---|---|
| Registered Trademark Agent, Canada (CPATA) | On the page before 2026-10-01 | [CPATA public register](https://registre-public-register.cpata-cabamc.ca/) |
| USPTO Patent Agent | On the page before 2026-10-01 | [USPTO practitioner roster](https://oedci.uspto.gov/OEDCI/) |
| University of Pennsylvania, Associate's Degree, AI (2022–2025) | On the page before 2026-10-01 | Confirm the exact credential title against the parchment |
| Macquarie University, Cyber Security: Essentials for Forensics (94.68%) | On the page before 2026-10-01 | Course certificate |
| Coursera, Introduction to Agile Development and Scrum (Apr 2026) | On the page before 2026-10-01 | Course certificate |
| Mohawk College, Business Administration & Management (2017–2019) | LinkedIn profile, self-reported | Published without a credential level, see held items |
| Course certificates: Microsoft, IBM, Google, University of Pennsylvania (AI Applications), Mimo (Python) | LinkedIn profile, self-reported | Listed as course certificates. None is a vendor certification such as Microsoft Certified or CompTIA A+ |

## Held until evidence is on file

| Claim | Why held | What publishes it |
|---|---|---|
| CISSP | ISC2 certification mark. Requires five years of paid experience and an endorsement | ISC2 member ID, then a link to [ISC2 member verification](https://www.isc2.org/MemberVerification) |
| "ISC2 Cybersecurity & Privacy certifications" | Ambiguous: does not name a credential | The exact credential (for example Certified in Cybersecurity) plus the ISC2 member ID |
| "ISACA" | ISACA is an association. It names no credential | The credential (CISA, CISM, CRISC, CGEIT or CDPSE) plus certificate number, then [ISACA verification](https://www.isaca.org/credentialing/verify-a-certification) |
| PMP, CAPM | PMI certification marks | Listing on the [PMI certification registry](https://www.pmi.org/certifications/certification-resources/registry) |
| CEH | EC-Council certification mark | Certification number, then [EC-Council verification](https://aspen.eccouncil.org/verify.aspx) |
| CPIM | ASCM certification mark | Listing on [ASCM verification](https://www.apics.org/verification) |
| "Bachelor of Business Administration", Mohawk College | The two-year span (2017–2019) is short for a bachelor's degree. The program is published, the credential level is not | The parchment or transcript naming the credential |
| 41% cut in compliance review time; under 10 minutes lateral-movement window; 41% rise in stakeholder confidence | No client, measurement or date on file. The same figure appears twice | A named or anonymized engagement with baseline, method and date |
| "348+ LinkedIn followers" | Goes stale, and the source URL (`linkedin.com/company/cleaglassinc`) does not match the company page the site links to (`clearglassinc`) | Not needed |

## Not adopted

| Item | Reason |
|---|---|
| `desmond@clearglassinc.com` | clearglassinc.com has no MX record. Mail bounces. `tests/test_contact_addresses.py` fails on it |
| "Toronto-based" | The site's address record and local SEO use Burlington, ON. The page says Burlington |
| FedRAMP, CMMC, CCCS alignment | An authorization claim. Out of scope for a founder bio |
| Sources [8]–[15] of the draft profile | They describe a different company: the UK ClearGlass start-up founded by Chris Sier ([corporate-adviser.com](https://corporate-adviser.com/chris-siers-clearglass-start-up-closes-2-6m-funding-round/)) |

## Publishing a held claim

1. Get the credential ID or the register listing.
2. Add the item to `#founderLedgerList` in `index.html` with `data-cat="certificate"`
   or `data-cat="designation"`, and an `<a class="ledger-status" data-status="register">`
   link to the issuer's verification page.
3. Update the entry count in `#founderLedgerCount`.
4. Move the row from "Held" to "Published" here.
5. Run `python -m pytest tests/test_founder_profile.py tests/test_homepage_integrity.py -q`.
