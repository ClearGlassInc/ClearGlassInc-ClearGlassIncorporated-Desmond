# ClearGlass Organic Social Growth Engine

**Status:** Active production system  
**Owner:** ClearGlass Inc. / Desmond Otieno  
**Objective:** Maximize organic reach, trust, leads, and conversions across X, LinkedIn, Threads, and owned assets without ad spend.

## Positioning

Technical leadership + executive credibility + category differentiation in cybersecurity oversight, AI agents, and governed intelligence systems.

**Ideal audience:**
- CISOs, security architects, IT leaders, and operations executives in Ontario / GTA / Canada
- Founders and COOs building AI-native companies
- Buyers of hardening, compliance, audit, and AI agent systems

**Transformation offered:** Clarity at scale — move from opaque risk and reactive firefighting to governed, auditable, AI-augmented operations.

## Content Pillars (map to funnel)

| Pillar | Funnel Stage | Primary Platforms | Goal |
|--------|--------------|-------------------|------|
| Technical Clarity | Awareness | X, LinkedIn | Teach specific problems + frameworks |
| Proof & Authority | Trust | LinkedIn, blog | Case patterns, audit outputs, system design |
| Contrast & Insight | Consideration | X threads, LinkedIn carousels | Challenge status-quo thinking |
| Direct Conversion | Conversion | All + email | Clear CTA to owned assets / discovery call |

## Operating Cadence

- **Daily:** 1 high-signal short-form asset (X or Threads) + strategic comments
- **3× week:** LinkedIn long-form or carousel
- **Weekly:** 1 deep insight piece (blog or thread) + repurposing pack
- **Monthly:** Performance review + pillar rebalance

## Conversion Paths (owned assets)

1. Profile / pinned post → landing page / blog → email list or discovery call
2. Thread / carousel → save → follow → direct message or form
3. Comment strategy → relationship → private conversation

## Metrics That Matter

- Reach & profile visits
- Saves, shares, meaningful replies
- Clicks to owned assets
- Email / community sign-ups
- Discovery calls booked
- Content reuse rate (repurposing efficiency)

## System Components

- `content-pillars.yaml` — source of truth for themes
- `agents/organic-growth-strategist/` — system prompt + agent config
- Workflows: `organic-daily.yml`, `organic-weekly-review.yml`, `organic-repurpose.yml`
- Output: `marketing/output/organic/` — ready-to-post assets
- Integration: feeds existing `bots/content_engine` and `daily-marketing-content`

## Activation

1. Workflows run on schedule + manual dispatch
2. Generated content lands as GitHub issues + markdown files
3. Human review → post → log performance back into the engine

This system is designed for compounding distribution and zero reliance on paid media.
