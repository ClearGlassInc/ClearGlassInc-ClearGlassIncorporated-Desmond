# Compliance Controls

- CASL/privacy/legal requirements must be reviewed by qualified counsel where needed; this repository does not provide legal advice.
- Outreach requires consent basis, recipient source, suppression check, message log, restrained follow-up limit, and opt-out handling.
- Advertising requires truthful claims, supported citations for factual performance claims, no fabricated urgency, approved budgets, and shutdown thresholds.
- Personal data must not be committed to the repository.

## Advertising controls (2026-10-02)

The controls below are enforced by `tools/campaign_registry.py`, except
AD-MEASUREMENT, which `tests/test_analytics_funnel_events.py` enforces. Each
one cites the sources it rests on in
[`data/compliance/advertising-sources.json`](../data/compliance/advertising-sources.json).
`tests/test_ad_governance.py` fails if a control loses its source, its
enforcement or its row here.

**What the sources are worth.** The owner supplied them on 2026-10-02. None was
fetched: this environment's egress proxy refused every host. They say where to
check, not what any page says today. They support the governance model; they
do not show that ClearGlass meets any platform, legal, privacy, security or
advertising requirement.

| Control | Rule | When | Sources |
|---|---|---|---|
| AD-CLAIMS | No absolute, performance or urgency claim in ad copy ("guaranteed", "unhackable", "100%", "fully compliant", "certified", "proven", "best", "limited time", ...) without a `substantiation` entry naming a file in this repository that proves it. Competition Act s. 74.01(1)(b) requires a performance claim to rest on an adequate and proper test made before it is published. | Always | Competition Bureau (basics, deceptive marketing), Ad Standards Code, Google Ads policies |
| AD-TARGETING | No audience or targeting on a sensitive personal trait: health or medical condition, disability, pregnancy, religion, ethnicity, sexual orientation, gender identity, political views, union membership, immigration status, criminal record, debt or financial hardship. An industry is not a trait. | Always | Google personalized advertising policy, LinkedIn and Microsoft ad policies, PIPEDA |
| AD-TRACKING | No remarketing, customer-list upload or conversion pixel while `legal/privacy.html` section 10 says ClearGlass deploys no advertising cookies or third-party tracking pixels. The policy changes first, with counsel; after that a dated legal review is required at approval. | Always | OPC meaningful consent, Google Consent Mode, Google personalized ads, NIST Privacy Framework |
| AD-DESTINATION | A landing page links the privacy policy, declares its language, gives every image a text alternative and every visible form field a label. | Always | PIPEDA (openness), WCAG 2.2, Google Ads destination requirements |
| AD-PLATFORM | For each platform the package carries ads for: the date the owner read its current ad policies, and its advertiser-verification state. | At approval | Google Ads policies and advertiser verification, Microsoft and LinkedIn ad policies |
| AD-ACCOUNT | Every login to the ad account uses multi-factor authentication. | At approval | CCCS baseline controls, NIST CSF 2.0 |
| AD-CASL | A package that sends email records its recipient list's consent basis (`express` or `implied`). Every message still passes `python -m bots.outreach_preflight`. | At approval | CRTC CASL guidance |
| AD-LEGAL | A dated review by qualified counsel when copy names compliance, privacy law, legal matters, insurance, regulators, OSINT or cross-border matters, or when targeting tracks visitors. | At approval | OPC privacy laws in Canada, Competition Bureau, Ad Standards Code |
| AD-MEASUREMENT | No personal information reaches an analytics provider, and no funnel event fires until the owner chooses a provider. | Always | Google Analytics data privacy, PIPEDA, NIST Privacy Framework |

### Recording approval

"Always" controls block a draft from READY FOR APPROVAL. "At approval" items
are the owner's to record when they move a campaign to `approved`, beside the
spend ceiling; `python3 tools/campaign_registry.py` lists what each draft still
needs, and `--check` fails an approved campaign that lacks any of them.

```json
"governance": {
  "policy_reviewed_on": {"google_ads": "YYYY-MM-DD", "linkedin_ads": "YYYY-MM-DD"},
  "advertiser_verification": {"google_ads": "verified", "linkedin_ads": "not_required"},
  "account_mfa": true,
  "casl_consent_basis": "express",
  "legal_review_on": "YYYY-MM-DD"
}
```

Dates must be real `YYYY-MM-DD` dates, not in the future. A recorded date is
the owner's statement; the tool cannot see the ad platform, so it checks that
the statement exists, not that it is true.

### Source hierarchy

When a source conflicts with another, the higher one wins:

1. The ad platform's current terms, advertising policies, data-processing terms, billing terms and verification requirements.
2. Canadian federal and Ontario privacy, consumer-protection, tax and commercial-electronic-message obligations.
3. ClearGlass's own published privacy policy, terms, service descriptions and substantiation records.
4. Written review by qualified Canadian legal, tax and privacy professionals where a campaign involves personal data, retargeting, security claims, legal-tech claims, cross-border processing or OSINT-related messaging.
5. Security baselines: NIST CSF 2.0 and the Canadian Centre for Cyber Security baseline controls.

### Known gaps

- The link supplied as "Government of Canada web accessibility guidance" is the
  Canada.ca Content Style Guide, which covers plain-language writing, not
  accessibility. The landing-page check follows WCAG 2.2.
- The landing-page check covers four WCAG 2.2 success criteria a parser can
  see (1.1.1, 1.3.1, 3.1.1, 3.3.2). Contrast, keyboard access, focus order and
  error messages need a manual or browser-based review.
- Microsoft Advertising has no campaign channel code yet. A `microsoft_ads`
  asset list is governed like the others, but adding the channel to `CHANNELS`
  is a reviewed change, because attribution reports depend on it.
