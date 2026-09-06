# Burlington Growth System Architecture

## Flow

Market signal → opportunity qualification → audience selection → offer selection → campaign brief → content and ad drafts → claim verification → compliance review → human approval → export/publication → performance collection → attribution → optimization recommendation → human-approved adjustment.

## Control planes

- `config/*.yaml`: brand, markets, offers, approval policies, suppression rules, and scoring models.
- `agents/*`: agent permissions, responsibilities, inputs, outputs, and forbidden actions.
- `bots/burlington_growth_engine.py`: deterministic guardrails for lead dedupe, suppression, approval checks, claims, budgets, geo targeting, audit integrity, rollback, prompt-injection sanitization, and loop prevention.
- `data/campaigns/burlington-campaign-packages.json`: initial campaign packages.
- `apps/command-center/index.html`: operational command center reading committed sample/draft state, not fictional live metrics.

## ClearGlassInc Artemis / Palantir integration blueprint

Gotham handles investigations and entity tracking; Foundry handles data integration, ontology, pipelines, and application logic; AIP handles copilots, agents, evals, and workflow automation; Apollo handles deployment, rollback, runtime policy, and version promotion. Self-improvement is limited to proposed prompt, workflow, heuristic, and routing changes that are evaluated, versioned, audited, and human-approved before activation.
