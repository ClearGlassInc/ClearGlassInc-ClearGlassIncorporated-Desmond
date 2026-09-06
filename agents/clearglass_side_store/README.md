# ClearGlass Side Store Agent

A production-grade **agent specification** for an autonomous, low-cost
wires-and-electronics storefront. This folder is the **instruction + scaffold
layer** — it defines how the agent should think and behave. It is **not** a
running store and does not move money on its own.

## What's here

| File | Purpose |
|---|---|
| `SOUL.md` | The agent's soul: identity, mission, skills, hard constraints, cadence, output contract. |
| `ETSY_FACTORY_CONNECT_AGENT.md` | Deterministic, fail-closed Etsy authentication, shop-identity, permission, and sync-readiness workflow. |
| `agent.json` | Machine-readable config (pricing, constraints, deployment tiers, integration status). |
| `agentic-workflow.template.yml` | A GitHub Actions **template** — reference only, intentionally not in `.github/workflows/`. |
| `README.md` | This file. |

## Real today vs. needs setup

**Real today (committed artifacts):**
- The SOUL spec, Etsy Factory Connect specification, machine-readable config,
  and workflow template.
- A coherent, internally-consistent ruleset an operator (or a future runtime)
  can follow.
- A fail-closed Etsy state machine that blocks listing publication, inventory
  synchronization, and order handling until every verification gate passes.

**Needs accounts, credentials, and human setup before anything executes:**
- A Shopify-compatible catalog and a deployed Next.js storefront.
- Stripe (payments), and `STRIPE_API_KEY` / `SHOPIFY_API_KEY` in GitHub Secrets.
- An Etsy developer application, approved redirect URI, owner-completed OAuth
  authorization, verified shop identity, approved least-privilege scopes, and
  secret-manager references. Never commit Etsy credentials or tokens.
- A production owner-approval record before Etsy publishing, inventory sync,
  buyer messaging, or order-management capabilities are activated.
- Real, human-approved suppliers and funding for inventory.
- Social / email / SMS accounts and tokens for marketing.

Until those exist, the workflow template stays out of `.github/workflows/`. If it
ran now it would fail on every tick and waste Actions minutes.

## Etsy connection status

The repository cannot prove that an Etsy shop is currently authenticated or
authorized. A public Etsy `people/...` profile URL is not shop authorization.
The current declared state is therefore `BLOCKED_USER_ACTION`.

Required sequence:

1. Complete Etsy authentication and consent through the approved Etsy surface.
2. Resolve and verify the exact shop name and server-derived shop ID.
3. Verify listing scopes through non-destructive API checks.
4. Verify order scopes without exposing buyer personal data.
5. Run a dry-run synchronization validation with no remote mutations.
6. Record production owner approval for the exact scopes and capabilities.
7. Activate only capabilities that passed every gate.

See `ETSY_FACTORY_CONNECT_AGENT.md` for the state machine, error taxonomy,
capability matrix, audit requirements, and required status output.

## Two deliberate corrections to the original brief

1. **Discount contradiction resolved.** The brief listed both *"never discount
   more than 15% without approval"* and a *"50% off first 10 orders"* launch
   promo. Those conflict. The default launch offer is now **15% off the first
   order + free shipping over $25** (within policy). A deeper promo is allowed
   only as an **explicit, time-boxed, budget-capped owner-approval exception** —
   never autonomous.
2. **Revenue target is a goal, not a promise.** "$1,000 in 14 days" is framed as
   a target that guides prioritisation. The agent optimises the controllable
   inputs (SKUs, listings, bundles, uptime, response time) and reports honestly
   when results diverge.

## Safety posture

Anything that touches **authentication, authorization, payments, billing,
orders, or personal data is Tier 3**: human-approved, audited, and reversible —
no autonomous production activation. Marketing is **consent-first (CASL)**:
consent on file, sender identified, one-click unsubscribe honoured. Secrets live
only in GitHub Secrets or the approved secret manager with least-privilege
access.

## Next step (opt-in)

After Etsy OAuth has been completed through the external account surface, run
the Factory Connect checks sequentially. Until authentication and permissions
are proven, the system must remain blocked and must not publish, synchronize, or
handle orders.

---

*ClearGlass Inc. · Burlington, Ontario · Clarity Is Power*
