# Head agent

The head agent turns a plain-language objective into a bounded set of tasks,
delegates each to one registered worker agent, runs them under leases and
limits, validates what comes back, and keeps a tamper-evident record. It is
built on the existing Agent OS pieces rather than beside them: routing comes
from the operator's capability registry (`operator.py`), risk scoring from the
governance gate (`governance.py`), ordering from the planner (`planning.py`),
and hashing from the audit ledger (`audit.py`).

It runs where the repository is checked out, because every capability is a
command in this repository. It is **not** part of the commerce control plane
and is not in that Docker image.

## The path a request takes

```
console or API client
  → bearer-token check (operator token; decisions need the approver token)
  → input validation (objective 3–500 chars, idempotency key, body ≤ 16 KB)
  → HeadAgent.plan: route → assign → order → score → persist   (tasks.sqlite3)
  → worker thread: claim under lease → tool-permission check → subprocess
       with timeout and allow-listed env → validate output → record evidence
  → mission status, events (hash chain), metrics
  → console polls GET /api/missions/{id} every 2 s while work is active
```

## Task contract

Every task row carries: `task_id`, `parent_task_id`, `correlation_id` (the
mission), `assigned_agent`, `objective`, `input`, `dependencies`, `status`,
`attempt`, `deadline`, `output`, `error`, `evidence`, and `created_at`,
`updated_at`, `started_at`, `finished_at`. Operational fields: `capability`,
`max_attempts`, `timeout_seconds`, `budget_seconds`, `risk`, `resource`,
`not_before`, `lease_owner`, `lease_expires_at`, `cancel_requested`,
`approved_by`.

States and the only allowed moves (`tasks.TRANSITIONS`):

| From | To |
|---|---|
| `waiting_for_approval` | `queued` (approved), `cancelled` (rejected or mission cancelled), `blocked` |
| `queued` | `running` (claimed), `cancelled`, `blocked` (upstream failed), `failed` (deadline passed) |
| `running` | `succeeded`, `failed`, `cancelled`, `queued` (timeout, interrupted, or lease lost; within the attempt budget) |
| `succeeded`, `failed`, `cancelled`, `blocked` | nothing; settled |

A mission's status is derived from its tasks, never stored: `running`,
`queued`, `waiting_for_approval` (including queued work that sits behind an
unapproved task), then `succeeded`, `failed`, `blocked` or `cancelled`.
`unmatched` means no capability matched and nothing was created.

## What keeps it safe to leave running

| Control | Where |
|---|---|
| No improvisation: an objective matching no capability creates no tasks | `HeadAgent.plan` |
| Writes, and anything the gate does not score LOW, wait for a human decision | `HeadAgent.plan` |
| The approver token must differ from the operator token; without one, every decision is refused | `server.Config` |
| Exactly one claim per task (`BEGIN IMMEDIATE` plus a conditional `UPDATE`) | `TaskStore.claim_next` |
| Leases: a dead worker's task is re-queued, or failed when its attempts are spent | `TaskStore.recover_expired` |
| One writer per work tree (`resource = "worktree"`), per-agent and global concurrency limits | `TaskStore.claim_next` |
| A failed or rejected task blocks everything downstream of it | `TaskStore._block_dependents` |
| Deadlines along the critical path, so slow upstream work is not mistaken for expiry | `HeadAgent.plan` |
| Only timeouts and interruptions are retried, with backoff of up to 60 s; a failing check is a finding | `HeadAgent._record` |
| Workers cannot delegate (`MAX_DEPTH = 1`), and nothing can assign work to the head | `TaskStore.create_mission` |
| The tool-permission check runs at execution time, not only at registration | `HeadAgent.work_once` |
| Child processes get `PATH`, locale, temp and proxy variables only, never the API tokens or service keys | `head.CHILD_ENV` |
| Output and log lines are redacted, then truncated to 32 KB per stream | `redaction.py`, `head._clip` |
| The event log is append-only (SQLite triggers) and hash-chained per mission | `TaskStore.events` |
| No capability deploys, pushes, sends a message or moves money | `agents.py` |

## Worker agents

| Agent | Capabilities | May write | Timeout × attempts | Concurrency |
|---|---|---|---|---|
| `repository` | `links.refresh` | work tree (gated) | 300 s × 2 | 1 |
| `verification` | `site.audit`, `links.check`, `workflows.audit`, `agentos.selfcheck`, `commerce.selfcheck`, `store.smoke` | no | 600 s × 2 | 2 |
| `integration` | `data.freshness`, `data.ieso.refresh`, `data.minerals.refresh` | feed files (gated) | 180 s × 2 | 1 |
| `security` | `security.secrets`, `security.workflows` | no | 300 s × 2 | 1 |
| `deployment` | `deploy.readiness` | no | 60 s × 1 | 1 |

`GET /api/agents` (or `python -m agent_os.head agents`) returns each agent's
full contract: purpose, allowed tools, data access, input and output schema,
limits, completion criteria and failure behaviour.
`agents.validate_registry()` must return `[]`, and the head agent refuses to
start otherwise.

## Live data

The site publishes two live feeds. Their fetchers already existed and record
provenance. The head agent runs them as gated `integration` tasks and reports
their freshness without fetching anything.

| Feed | Provider | Fetcher | Written to | Freshness policy | State on 2026-10-22 |
|---|---|---|---|---|---|
| IESO demand and supply mix | `reports-public.ieso.ca` (public reports) | `scripts/ieso_public_feed.py` | `data/grid/ieso-public.json` | warning 3 h, stale 6 h | **never retrieved**: every recorded attempt was refused by the network |
| Critical-minerals policy and news | `api.io.canada.ca` (Government of Canada news) | `scripts/minerals_data_sync.py` | `feeds/minerals/` | the manifest's own per-feed thresholds | **never retrieved**: the feed status is `UNAVAILABLE` |

Neither feed needs a credential. The blocker is network egress from wherever
the fetcher runs. Since 2026-09 the scheduled workflows that fetched them have
not run (Actions dispatches no runners), so the head agent is now the way to
refresh them from an operator host:

```bash
python -m agent_os.head run "refresh ieso grid data and check data freshness"
# the refresh waits for approval; approve it, then the freshness check runs after it
CG_LIVE_FEEDS=1 python -m pytest tests/test_live_feeds.py -q   # opt-in provider check
```

A refresh that cannot reach its provider exits non-zero, keeps the last good
snapshot, records the error in the feed file, and blocks the dependent
freshness task. The console shows the source as `never retrieved` or `stale`,
never as healthy.

## Running it

```bash
cp agent_os/.env.example .agent_os.env       # fill in two different tokens
set -a; . ./.agent_os.env; set +a
python -m agent_os.server                     # http://127.0.0.1:8765/
```

The CLI works without the server, against the same database:

```bash
python -m agent_os.head run "run a security review and check data freshness"
python -m agent_os.head plan "regenerate links then link check"
python -m agent_os.head approve tsk-… --approver "Desmond" --reason "reviewed"
python -m agent_os.head work            # process the queue until SIGTERM
python -m agent_os.head status msn-…
python -m agent_os.head events msn-…    # hash chain and verification
python -m agent_os.head metrics
```

The CLI has no token check, because anyone who can run it can already open the
database file. Protect `.agent_os/` with file permissions.

## Operating it

- **Health.** `GET /healthz` means the process answers. `GET /readyz` means the
  store answers and at least one worker has reported in the last 15 s; it
  returns 503 otherwise.
- **Restart or crash.** State is in SQLite. Running tasks whose lease lapses
  are re-queued on the next claim, or failed if their attempt budget is spent.
- **Shutdown.** SIGTERM stops new requests, gives running commands
  `AGENT_OS_SHUTDOWN_GRACE` seconds, then stops them and re-queues them.
- **Logs.** JSON lines on stderr, with `correlation_id` and `task_id` and
  credentials redacted.
- **Metrics.** `GET /api/metrics` reports tasks by status and by agent, queue
  depth, items awaiting approval, the oldest queued age, retries, mean duration
  per capability, and per-source data freshness.
- **Exposure.** The server binds to 127.0.0.1. Anything wider needs TLS in front
  of it; the bearer tokens must not cross a network in clear text.
- **Backups.** `.agent_os/tasks.sqlite3` is the whole record. Copy it while the
  server is stopped, or use `sqlite3 .backup`.

## Verifying a change

```bash
ruff check agent_os tests/test_agent_os_head.py tests/test_agent_os_server.py
python -m pytest tests/test_agent_os*.py -q
python -m agent_os.head run "check data freshness"     # a real capability, end to end
```
