# ClearGlass Control Surface — Event Contract & Endpoint Specification

> Canonical contract between the **n8n event ingress layer** and the read-first
> dashboard at [`saas-platform.html`](../saas-platform.html).
> Machine-readable schema: [`contracts/control-surface-events.schema.json`](./contracts/control-surface-events.schema.json)
> Status: **v1.0** · Owner: ClearGlass Inc. · Surface: GitHub Pages (public, read-only)

---

## 1. Principles

1. **Read-first control plane.** The dashboard only issues `GET` requests to six
   approved, non-sensitive endpoints. No write, no mutation, no credentials in
   the browser. Any admin action lives in a separate authenticated tool.
2. **n8n is the only ingress.** Producers (bots, workflows, GitHub Actions,
   monitors) POST events to a single n8n Webhook node. n8n normalizes every
   event into the envelope below before anything reaches a dashboard endpoint.
3. **Stable envelope, additive evolution.** Fields are never renamed or
   repurposed. New fields are additive and optional. Consumers must ignore
   unknown fields.

---

## 2. Event envelope (ingress → n8n)

Every event POSTed to the ingress webhook MUST normalize to:

```json
{
  "type": "activity.append",
  "title": "Webhook received",
  "status": "ok",
  "value": null,
  "timestamp": "2026-06-12T14:31:07Z",
  "source": "n8n/daily-ingest",
  "severity": "info"
}
```

| Field       | Type                | Required | Rules |
|-------------|---------------------|----------|-------|
| `type`      | string (enum)       | yes      | One of `metrics.update`, `activity.append`, `health.ping`, `alert.raise` |
| `title`     | string ≤ 120 chars  | yes      | Human-readable headline; plain text only (renderer escapes HTML) |
| `status`    | string (enum)       | yes      | `ok` \| `warn` \| `bad` — drives the tag colour on the dashboard |
| `value`     | string \| number \| object \| null | yes (nullable) | Payload body; shape depends on `type` (see §3) |
| `timestamp` | string (ISO 8601, UTC) | yes   | Producer time; n8n stamps receipt time if absent |
| `source`    | string ≤ 80 chars   | yes      | `system/component` form, e.g. `github/pages-deploy`, `n8n/lead-sync` |
| `severity`  | string (enum)       | yes      | `info` \| `warn` \| `critical` — alert routing, independent of display `status` |

**Normalization rules (n8n):**
- Missing `timestamp` → set to receipt time (UTC, ISO 8601).
- Missing `severity` → `info`. Missing `status` → `ok`.
- `title`, `source` are truncated to their limits; control characters stripped.
- Events failing validation are dropped to a dead-letter list, never surfaced.

---

## 3. Event groups

### 3.1 `metrics.update`
Replaces an overview metric. `value` carries the metric object:

```json
{
  "type": "metrics.update",
  "title": "Active agents",
  "status": "ok",
  "value": { "label": "Active agents", "value": "47", "delta": "+3 this hour", "pct": 68 },
  "timestamp": "2026-06-12T14:30:00Z",
  "source": "bot-orchestrator/run-12",
  "severity": "info"
}
```

### 3.2 `activity.append`
Appends one row to the live activity feed. `value` may be `null` (title +
status + source suffice) or carry `{ "detail": "..." }`.

### 3.3 `health.ping`
Heartbeat per service. `value`:

```json
{ "service": "pages", "uptime": "99.94%", "detail": "All core services reachable" }
```

A service missing two consecutive pings is marked degraded by the aggregator.

### 3.4 `alert.raise`
Surfaces an item in **Alerts and exceptions**. `severity: "critical"` alerts
are also mirrored into the activity feed. `value`:

```json
{ "detail": "No update in 16 minutes.", "runbook": "docs/CI_RUNBOOK.md" }
```

---

## 4. Read endpoints (n8n → dashboard)

All endpoints: `GET`, JSON, public-safe, **no auth**, no PII, no secrets.
The dashboard polls with `cache: "no-store"` every 30 s.

| # | Endpoint    | Returns | Renders into |
|---|-------------|---------|--------------|
| 1 | `/metrics`  | `Metric[]` | Overview metric cards |
| 2 | `/activity` | `FeedItem[]` (newest first, ≤ 50) | Live activity feed |
| 3 | `/pipeline` | `Counter[]` | Lead pipeline |
| 4 | `/health`   | `Health` | System health panel |
| 5 | `/alerts`   | `AlertItem[]` (active only) | Alerts and exceptions |
| 6 | `/runs`     | `FeedItem[]` (latest ≤ 20) | Recent workflow executions |

### Response shapes (must match the renderer exactly)

```ts
type Status   = "ok" | "warn" | "bad";

interface Metric    { label: string; value: string; delta?: string; pct?: number /* 0–100 */ }
interface FeedItem  { title: string; status: Status; detail: string; time?: string; timestamp?: string }
interface Counter   { label: string; value: string }
interface Health    { status: string; uptime: string; detail: string }
interface AlertItem { status: Status; title: string; detail: string }
```

**Contract guarantees**
- Arrays may be empty, never `null`. Unknown fields are ignored by the renderer.
- All strings are plain text; the dashboard HTML-escapes everything it prints.
- `4xx/5xx` or timeout → the dashboard falls back to bundled placeholder data
  and shows `Node: degraded`; endpoints must therefore never be load-bearing
  for page render.

**Transport requirements**
- `Access-Control-Allow-Origin: https://www.clearglassinc.com` (no `*` once live).
- `Cache-Control: public, max-age=15` recommended at the edge to absorb polling.
- Rate limit by IP at the ingress proxy; the dashboard generates ≤ 12 req/min.

---

## 5. n8n reference wiring

```
[Webhook POST /events]                 ← producers (bots, Actions, monitors)
        │
[Code: validate + normalize envelope]  ← §2 rules; invalid → dead-letter list
        │
[Switch on type]
   ├─ metrics.update  → [Data Store: metrics (upsert by label)]
   ├─ activity.append → [Data Store: activity (ring buffer, 50)]
   ├─ health.ping     → [Data Store: health (latest per service)]
   └─ alert.raise     → [Data Store: alerts (active set)] ─ critical? → also activity
        │
[6 × Webhook GET]  /metrics /activity /pipeline /health /alerts /runs
                   each reads its store and returns the §4 shape
```

- The ingress webhook URL is a secret shared only with producers; it accepts
  POST only and returns `202` on accept, `422` on validation failure.
- `/pipeline` counters may alternatively be refreshed on a schedule from the
  CRM rather than event-driven; the read contract is identical.
- When the endpoints are live, set them in `saas-platform.html` →
  `const endpoints = {...}` (the only edit the page needs).

---

## 6. Versioning & change control

- This file + the JSON Schema are the source of truth; change via PR only.
- Breaking changes require a `/v2` endpoint namespace and a new schema `$id`.
- Validate producer payloads against
  [`contracts/control-surface-events.schema.json`](./contracts/control-surface-events.schema.json)
  in CI (e.g. a tests/ case per event group).
