# ClearGlassInc YouTube Production and Revenue Operations

## Objective and accountable roles

Ship evidence-led content on schedule without weakening rights, privacy, security, disclosure, or human-approval boundaries. In a modest startup configuration one person may hold multiple roles, but **fact-check approval must be a second-person review** for security, finance, platform-policy, sponsor, or customer claims.

| Gate | Responsible | Required evidence |
|---|---|---|
| Topic | Growth Director | Search intent, audience job, pillar, unique contribution |
| Claims | Researcher + second reviewer | Claim-level evidence register; current primary/authoritative sources |
| Script | Executive Producer | Hook, open loop, payoff, CTA, safety boundary |
| Rights | Producer | Asset source, licence, permission/release, attribution requirements |
| Publish | Channel Owner | Caption QA, metadata, disclosures, links, policy check, approval record |
| Revenue | Founder | Offer accuracy, capacity, pricing, disclosure, approval |
| Review | Growth Director | 24h/7d/28d cohort metrics and one documented decision |

## Kanban and service levels

`Idea → Qualified → Researching → Scripted → Fact check → Ready to record → Editing → Publish QA → Scheduled → Published → 24h review → 7d review → 28d review → Repurpose/archive`.

Maintain a two-video ready backlog. Stop the line for an unsourced material claim, exposed secret/personal data, missing licence, unsafe demonstration, broken consent flow, undisclosed material relationship, or inaccurate title/thumbnail.

## Repeatable production pipeline

1. **Research (90 min):** write the viewer decision, search query, freshness window, and counterclaim. Prefer law/regulator/standards/vendor documentation or original research. Save URL, author/publisher, date, retrieval time, scope, and a paraphrase. Never let an AI-generated citation enter the script before a human opens it.
2. **Script (75 min):** result in five seconds; context after value; a visual change every 20–40 seconds; one worked example; one objection; recap; one primary CTA. AI may propose drafts but may not invent experience, sources, quotes, metrics, or product capability.
3. **Safety/fact check (30–60 min):** verify every mutable fact immediately before recording; test links; label demonstrations/simulations/target-state; remove live targets, exploit-enabling detail, private data, keys, addresses, balances, customer names, or privileged UIs.
4. **Record (45 min):** phone capable of 1080p, CAD 50–120 wired/lavalier mic, window/key light, quiet treated room, tripod, teleprompter near lens. Capture two cold opens and 10 seconds room tone.
5. **Edit (2–4 h):** remove preamble/dead air, preserve technical qualifiers, normalize intelligibility, use owned/licensed music, add source cards and visual labels, export 1080p H.264 plus archive master.
6. **Captions/transcript (30 min):** AI transcription is a draft. Human-correct names, technical terms, negations, amounts, URLs, and speaker changes. Upload caption file; publish transcript where practical.
7. **Thumbnail test (30 min):** create two genuinely distinct concepts before publish. No fabricated interface, consequence, identity, or expression. Test at phone size and grayscale. Use YouTube’s native test feature when available; otherwise one recorded post-publication change under the decision rules.
8. **Publish QA (30 min):** unlisted review on phone and TV; title/description/chapters; disclosures; category/language; checks; end screen; related link; playlist; captions; UTM; pinned comment; source/correction section. Second human signs the release checklist.
9. **Distribution (45 min):** email the segment that requested this topic; publish one native LinkedIn insight and one site excerpt; avoid duplicate spam; reply to substantive comments without soliciting empty engagement.
10. **Performance review:** capture 24h, 7d, 28d data by traffic source. Diagnose topic, packaging, hook, body, CTA, or offer separately. Change one variable and record it.

## Evidence register template

```csv
claim_id,exact_claim,source_url,publisher,published_or_updated_at,retrieved_at_utc,scope_or_version,evidence_excerpt_location,script_timecode,reviewer,status
C01,"",,"",,,"","","",,"blocked"
```

Allowed status transitions: `blocked → verified → expired/corrected`; only a human reviewer moves a claim to verified. Quotes require timestamp/page and rights review. Capture source snapshots only where terms and copyright permit.

## Script and edit template

```text
0:00 RESULT/HIDDEN RISK — proof before identity
0:05 VIEWER CONTRACT — what they can do by the end
0:20 CLAIM + SOURCE CARD
0:45 CONTROL 1
1:45 CONTROL 2
2:45 CONTROL 3
3:45 LABELED WORKED EXAMPLE / PATTERN INTERRUPT
5:10 CONTROL 4
5:50 OBJECTION / LIMIT
6:20 CONTROL 5
6:50 FIVE-CARD RECAP
7:10 ONE PRIMARY CTA + WATCH NEXT
```

## Release checklist

- [ ] Viewer intent and unique contribution are explicit.
- [ ] Every factual claim is verified; unknowns remain unknown.
- [ ] No secrets, personal data, unsafe target detail, or unapproved customer material.
- [ ] Demonstration, simulation, composite, and target-state visuals are labeled.
- [ ] Asset licences/releases and AI/synthetic-content decision are recorded.
- [ ] Affiliate/sponsor disclosure is spoken, on screen, in the first description lines, and declared in YouTube settings when applicable.
- [ ] Title/thumbnail accurately represent delivered content; thumbnail has ≤4 words.
- [ ] Captions, transcript, contrast, pronunciation, audio, and reduced-motion concerns pass.
- [ ] Description, chapters, tags, playlist, end screen, pinned comment, and correction path pass.
- [ ] Primary CTA, landing page, UTM, consent, privacy, email delivery, unsubscribe, and CRM attribution pass with a test record deleted afterward.
- [ ] Channel owner and second reviewer approved the exact upload.

## Funnel and disclosure templates

**Top description:**

```text
Download [RESOURCE]: [UTM LINK]
Educational content—not legal, investment, or individualized security advice.
[If applicable] Paid partnership with [SPONSOR]. ClearGlassInc retained editorial control.
[If applicable] Affiliate link: ClearGlassInc may earn a commission at no extra cost to you.
```

**Consultation intake:** business email, organization, role, jurisdiction, desired outcome, systems/data classes in broad categories, timeline, and consent. Explicitly instruct: “Do not submit passwords, keys, incident evidence, personal data, wallet seed phrases, or classified/restricted information.” Rate-limit and encrypt the form; use retention/deletion rules.

**Sponsor package after evidence exists:** sponsor fit and exclusions; audience facts from YouTube Analytics with date range; fixed deliverables; disclosure treatment; editorial independence; claims substantiation; revision boundary; cancellation/brand-safety terms. Never guarantee impressions, leads, sales, or positive coverage.

## Weekly scorecard

```csv
week,video_id,format,pillar,published_at,impressions,ctr_pct,views,retained_30s_pct,watch_hours,avd_seconds,returning_viewers,net_subscribers,subs_per_1000_views,landing_sessions,consented_signups,qualified_leads,sales,net_revenue_cad,production_cost_cad,decision,owner,review_at
```

Calculated fields:

```text
subs_per_1000_views = 1000 * net_subscribers / views
lead_rate = qualified_leads / landing_sessions
revenue_per_video = attributed_net_revenue / videos_in_cohort
contribution = attributed_net_revenue - refunds - affiliate_reversals - production_cost
```

Use denominator guards and report unavailable, not zero, when YouTube withholds a metric. Keep raw exports access-controlled. Do not join identifiable viewing behavior to CRM records without appropriate consent and a documented privacy basis.

## Issue and correction protocol

1. Freeze promotion; unlist if continued exposure creates material harm or deception.
2. Preserve source, upload version, analytics, report, and decision trail.
3. Classify: caption typo, non-material clarification, material factual error, rights/privacy/security breach.
4. Correct visible metadata/caption for minor issues. For material issues, add a clear correction, notify affected parties as required, and publish a corrected version only after re-review.
5. Record root cause and add a preventive checklist/eval. Deletion is not a substitute for audit evidence.

## Budget

Use an existing recent phone and computer first. Initial incremental target: CAD 150–400 for mic, tripod, light, acoustic treatment, storage, and licensed assets. Use free/low-cost editing and design tools where their terms, privacy, and export quality fit. Approve recurring AI/editing/SEO subscriptions only after a four-week time-saving measurement; never upload sensitive material merely for convenience.
