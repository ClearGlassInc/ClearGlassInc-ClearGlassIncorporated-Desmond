# ClearGlassInc YouTube Launch System

**Owner:** Desmond Otieno Odhiambo
**Positioning:** See Through Everything.
**Operating principle:** Transparency is infrastructure. Clarity is power.
**Status:** Production plan; publishing, claims, sponsor acceptance, affiliate enrollment, and platform actions require human review.

This directory is the source-controlled launch system for a 90-day YouTube program serving Canadian and global entrepreneurs, executives, technology professionals, investors, and security-conscious consumers.

## Deliverables

- [`STRATEGY.md`](STRATEGY.md): niche, promise, identity, channel copy, trailer, pillars, playlists, cadence, conversion architecture, monetization, metrics, decision rules, launch checklist, scenarios, and policy verification.
- [`content_catalog.json`](content_catalog.json): canonical production records for 24 long-form videos, 60 Shorts, 12 community posts, and 13 livestreams.
- [`generated/PRODUCTION_BOOK.md`](generated/PRODUCTION_BOOK.md): production-ready briefs and scripts generated from the catalog.
- [`OPERATIONS.md`](OPERATIONS.md): research-to-review pipeline, evidence register, QA gates, templates, UTM standard, disclosures, and weekly scorecard.
- [`ARTEMIS_SERIES.md`](ARTEMIS_SERIES.md): technically credible, governed ClearGlassInc Artemis series blueprint; it treats Palantir integration as target-state unless verified in an authorized environment.
- [`tools/build_production_book.py`](tools/build_production_book.py): deterministic generator and schema/count validator.

## Canonical workflow

```bash
python3 youtube_launch/tools/build_production_book.py --check
python3 youtube_launch/tools/build_production_book.py
```

Edit `content_catalog.json`, never the generated production book. Every factual claim still requires a source in the episode evidence register before recording. Never paste secrets, private customer data, restricted intelligence, or unapproved Palantir material into an AI tool.
