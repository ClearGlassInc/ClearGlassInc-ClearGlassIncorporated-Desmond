# Self-Evolving Wealth Engine

Two bots that turn the standing wealth strategy into an automated, self-improving
loop. They plug into the existing fleet (registry → runner → orchestrator) and
follow the same deterministic, no-network, audit-friendly conventions as every
other ClearGlass bot.

> **A trust with no assets is like a vault with nothing inside.**

## Priority order (non-negotiable sequence)

```
1. Revenue            ← fastest legal way to get paid now
2. Corporation        ← ClearGlass Inc. wraps proven revenue
3. Business Credit    ← trade lines under the corp
4. Investment Assets  ← holding company accumulates appreciating assets
5. Trust              ← LOCKED until assets clear the floor
```

Full sequence: **ClearGlass Inc. → Revenue → Corporate Credit → Holding Company → Family Trust**

---

## 1. `wealth_ladder_bot` — the strategy engine

Reads an optional ledger (`operations/wealth_ladder/ledger.json`, see
`ledger.example.json`), evaluates every rung in priority order, and emits the
day's focus plus a "fastest legal way to get paid now" plan.

Key behavior — **the trust is gated behind real assets**. The Trust rung stays
`🔒 locked` until `investable_assets >= $100,000` (`TRUST_ASSET_FLOOR`). Below
that, its rationale is literally the thesis above. This encodes the strategic
reality: under roughly six figures, a trust usually creates legal bills before
it creates income.

The "fast cash" track surfaces, in parallel:
- **Benefit-eligibility reviews** (review prompts, *not advice* — evaluate with a
  qualified professional): Canada Disability Benefit, Disability Tax Credit,
  CPP Disability.
- **ClearGlass income-producing services**, fastest-to-cash first: AI risk
  assessments, cybersecurity audits, compliance consulting, AI automation
  implementation.

```bash
python -m bots.wealth_ladder_bot --print          # render to stdout
python -m bots.wealth_ladder_bot                  # write latest.* + archive
python scripts/bot_runner.py wealth_ladder        # via the fleet runner
```

Outputs: `operations/wealth_ladder/latest.{md,json}` (+ timestamped archive).

## 2. `self_evolving_engine` — the "automate itself" layer

The bot that improves the bot fleet. Each generation it:

1. Reads fleet run history (`operations/output/bot_run_log.json`).
2. Loads its persisted **genome** (`operations/output/self_evolving/genome.json`)
   — weights, quarantine list, and lineage. This memory is what lets it *evolve*
   across runs instead of starting cold.
3. Scores each bot's **fitness** from reliability + recency + alignment to the
   wealth-ladder priority order (Revenue-adjacent bots get a bias).
4. **Mutates**, with a hard safety split:
   - *Low-risk, auto-applied:* bounded routing-weight nudges toward what works.
   - *Higher-risk, approval-gated:* quarantining a chronically failing bot is
     only ever **proposed** (`requires_human_approval: true`), never auto-applied.
5. Increments the generation, appends a lineage record, and persists the genome
   so the next run inherits it.

Weights are clamped to `[0.10, 3.00]` so the fleet can't runaway-evolve in one
generation.

```bash
python -m bots.self_evolving_engine --print       # dry run, no genome write
python -m bots.self_evolving_engine               # evolve one generation
python scripts/bot_runner.py self_evolving        # via the fleet runner
```

Outputs: `operations/output/self_evolving/{genome,latest_proposal,latest_fitness}.json`.

## Orchestration

Both are registered in `bots/config/bot_registry.json` and
`scripts/bot_runner.py`. In `bots/master_orchestrator.py`:

- `wealth_ladder` has no dependencies (runs in the first wave).
- `self_evolving` depends on `wealth_ladder`, `operations`, and `site_health`,
  so it runs **last** — after the bots whose outcomes it scores.

## Guardrails

- Deterministic and pure given inputs; no network calls in either module.
- Structural fleet changes are always human-gated.
- All figures are operator-supplied via the ledger; nothing is asserted as
  eligibility, legal, tax, or financial advice.
