# ClearGlassInc Artemis Growth Engine

This directory is the review layer for repository-led growth. The system converts verified repository facts into channel-specific campaign drafts and tracked links without auto-posting, fabricating outcomes, incentivizing engagement, or scraping GitHub users.

## Operating model

```text
Repository evidence
  -> Artemis Growth Engine
  -> validation gates
  -> UTM-tagged draft assets
  -> human review
  -> manual publication
  -> aggregate measurement
```

## Generate the campaign pack

```bash
python -m bots.artemis_growth_bot
```

The generator writes:

- `marketing/output/threads_latest.md`
- `marketing/output/threads_latest.json`
- `marketing/output/campaign_latest.md`
- `marketing/output/campaign_latest.json`
- `marketing/output/threads_archive/<timestamp>.md`
- `threads.html` as a `noindex,nofollow` internal review surface

## Safety and conversion invariants

1. Every generated campaign asset includes repository evidence paths.
2. Every external campaign destination is HTTPS and host-allowlisted.
3. Campaign links carry `utm_source`, `utm_medium`, `utm_campaign`, and `utm_content`.
4. Generated assets are always `review_required=true`.
5. Publication mode is hard-coded to `manual-review-only`.
6. The generator rejects unresolved placeholder syntax and prohibited promotional patterns.
7. It does not post to social platforms, message users, create fake engagement, buy stars, mass-follow accounts, or fabricate customer outcomes.

## Channels currently generated

- LinkedIn launch post
- X launch post
- Reddit technical-feedback post
- Dev.to article brief
- Hacker News Show HN brief
- Five proof-led technical threads

## Verification

```bash
python -m unittest tests.test_artemis_growth_bot
```

The tests verify allowlisted destinations, UTM tagging, review gating, generation of all campaign artifacts, and rejection of known fabricated/manipulative language.

## Source of truth

Campaign claims must remain traceable to `README.md`, `docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md`, or another explicit repository path. If a claim cannot be supported by repository evidence or permissioned real-user proof, do not publish it.
