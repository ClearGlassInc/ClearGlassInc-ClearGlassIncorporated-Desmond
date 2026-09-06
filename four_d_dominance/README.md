# 4-D Dominance System

A stdlib-only, working implementation of the framework described in
[`4D_DOMINANCE_ACTIVATION.md`](../4D_DOMINANCE_ACTIVATION.md). It coordinates
work across four domains — **Web, AI, Corporate, Brand** — with an
orchestrator-first, multi-agent design.

## Architecture

```
Orchestrator  (classify → plan → execute/critique → escalate)
   ├─ ModelRouter   tiered backends: Pro / Flash / Flash-Lite (mock by default)
   ├─ Planner       decomposes a task into research → draft → self-review
   ├─ Executor      drafts each step
   ├─ Critic        scores drafts 0–100, drives the revision loop
   ├─ Memory        short-term buffer + long-term JSON store
   └─ Governance    scores every action 0–100 and gates risky ones for approval
```

### Safety model

The governance gate mirrors the commerce control plane
(`clearglass-commerce/control-plane/app/governance.py`) and the repository
invariant: **read-only analysis → draft → human approval → execution.**

- **low** (analysis, drafting, reporting) → auto-execute + log
- **medium** (publish/post/distribute/commit) → held for approval
- **high / critical** (go-live, pricing, payment, refund, fulfillment, mass
  outbound) → blocked pending a human approval

The pipeline runs in **dry-run** mode: it produces drafts and plans, never
publishes or deploys. Every step is written to an append-only audit trail.

## Run it

```bash
# all four domains, human-readable summary
python -m four_d_dominance.pipeline --all

# one domain, full JSON report to stdout
python -m four_d_dominance.pipeline --domain web --json

# write the report into a directory
python -m four_d_dominance.pipeline --all --output four_d_dominance/output
```

No API keys are required — the default `ModelRouter` backend is a deterministic
offline mock (the same "mock mode" philosophy as the commerce store). To plug in
a real provider, pass a `backend` callable:

```python
from four_d_dominance import ModelRouter, Orchestrator

def my_backend(tier, prompt):
    ...  # call your provider, return the completion text

orch = Orchestrator(router=ModelRouter(backend=my_backend))
outcome = orch.run_task("Draft a thought-leadership article outline")
print(outcome.summary())
```

## Tests

```bash
python -m pytest tests/test_four_d_dominance.py -q
```

## GitHub Actions

`.github/workflows/master-orchestrator.yml` is the master pipeline. It fans out
to one reusable workflow per domain, each running the pipeline in dry-run mode:

| Domain    | Workflow                                    |
|-----------|---------------------------------------------|
| Web       | `.github/workflows/seo-optimizer.yml`       |
| AI        | `.github/workflows/agent-deployer.yml`      |
| Corporate | `.github/workflows/thought-leadership.yml`  |
| Brand     | `.github/workflows/viral-content.yml`       |

Trigger it manually from the Actions tab (`workflow_dispatch`) or on the
built-in 6-hour schedule.
