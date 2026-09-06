# ClearGlass Autonomous Agent OS v8.0 — Blueprint

> Executive orchestration layer of the ClearGlass Autonomous Intelligence
> Platform: a deterministic, governed, multi-agent operating system for
> planning, reasoning, execution, auditing, security, and continuous
> optimization.

**Status:** the agent *definition* and a *runnable, tested governance runtime*
below are provisioned and CI-gated in this repo. The executive loop, the DAG
planner, the expected-value strategy ranker, the multi-source intelligence
resolver, the ranked memory store, the recovery engine, the learning loop, and
the tamper-evident audit ledger are all implemented and unit-tested. What is
deliberately *not* wired is live external connectors for each specialist (real
analytics/Stripe/social APIs) — those are integration points that must pass
through the same approval gate. Nothing here moves money, deploys, or mutates
production.

---

## Where it lives

| Artifact | Path |
|----------|------|
| Agent definition (contract) | `agents/clearglass_agent_os/agent.json`, `system_prompt.md` |
| Runtime (executable) | `agent_os/` |
| Governance + approval gate | `agent_os/governance.py` |
| Sub-agent roster | `agent_os/roster.py` |
| Planning DAG | `agent_os/planning.py` |
| Executive strategy ranking | `agent_os/executive.py` |
| Intelligence / contradiction detection | `agent_os/intelligence.py` |
| Ranked memory | `agent_os/memory.py` |
| Recovery engine | `agent_os/recovery.py` |
| Learning loop | `agent_os/learning.py` |
| Tamper-evident audit ledger | `agent_os/audit.py` |
| Executive orchestrator | `agent_os/orchestrator.py` |
| Self-check + CLI | `agent_os/self_check.py`, `agent_os/__main__.py` |
| Tests | `tests/test_agent_os.py`, `tests/test_agent_os_advanced.py` |
| Executor workflow | `.github/workflows/agent-os.yml` |

## Primary directive

Maximize measurable business value while minimizing operational risk. Every
decision must improve at least one of: **revenue, automation, accuracy,
security, intelligence, scalability, compliance, knowledge.**

## Core principles

Never hallucinate · never fabricate evidence · never hide uncertainty · always
expose confidence · every action explainable · every output reproducible ·
every conclusion references supporting evidence.

## The thirteen sub-agents

Executive · Planning · Intelligence · Research · Coding · Security · Financial ·
Marketing · Automation · Memory · Audit · Recovery · Learning
(`agent_os/roster.py`).

## Advanced features (implemented)

- **Executive expected-value ranking** — strategies scored
  `p·value − cost − risk·value`; the highest-EV option is chosen, fallbacks are
  surfaced as optimization opportunities.
- **Multi-source intelligence** — claims resolved per entity; a lone source is
  capped (never treated as truth), disagreement flags a contradiction and
  penalises confidence. Mission confidence is the **minimum** signal observed.
- **Ranked memory** — recall scored `accuracy × recency × authority`; unrelated
  memories are excluded and missing memory is reported as missing.
- **Recovery engine** — failure signals classified into the seven root causes;
  transient causes get bounded exponential backoff, deterministic faults
  escalate immediately (fail closed).
- **Learning loop** — outcomes rolled up into success rate / mean duration,
  failures turned into lessons, slow successes flagged for optimization.
- **Tamper-evident audit ledger** — every decision is written to a SHA-256 hash
  chain; `verify()` detects any post-hoc edit and reports the first broken link.

## Governance model (the non-negotiable core)

Invariant: **read-only analysis → draft → human approval → execution.**

Every proposed action is scored 0–100 and routed:

| Tier | Examples | Policy |
|------|----------|--------|
| **low** | read metrics, collect evidence, draft copy/plan, run audit | auto-execute + log |
| **medium** | update catalog, publish content, open PR, run A/B test | queue for review |
| **high** | update pricing, send outbound, launch campaign, provision infra, rotate secret | approval required |
| **critical** | payment settings, refunds, delete data, deploy production, modify access control | approval required, highest scrutiny |

**Always-escalate**, regardless of score: money, production deploys,
access-control changes, data deletion, secret rotation, mass outbound.

**Fail closed** on every axis: unknown actions default to high; missing
confidence or missing evidence forces escalation; any scoring error resolves to
"approval required". This mirrors the commerce OS gate in
`clearglass-commerce/control-plane/app/governance.py`.

## Decision framework (per action)

1. Understand objective · 2. Identify constraints · 3. Gather evidence ·
4. Generate multiple strategies · 5. Estimate probability of success ·
6. Estimate cost · 7. Estimate risk · 8. Choose highest expected value ·
9. Verify · 10. Execute · 11. Audit · 12. Learn.

## Output contract

Every workflow returns: Mission Summary · Objective · Assumptions ·
Dependencies · Execution Plan · Risk Assessment · Evidence · Confidence Score ·
Artifacts Produced · Validation Results · Rollback Plan · Optimization
Opportunities · Next Recommended Actions — emitted as the `MissionReport`
dataclass in `agent_os/orchestrator.py`.

## Run & verify

```bash
python -m agent_os                     # end-to-end governed demo mission (JSON)
python -m agent_os.self_check          # governance + audit self-check + report
python -m agent_os.self_check --json   # machine-readable
pytest tests/test_agent_os.py tests/test_agent_os_advanced.py -q
```

The `Agent OS Self-Check` workflow runs these on a schedule, on PRs touching
`agent_os/**`, and on demand; it fails closed if any invariant is violated.
