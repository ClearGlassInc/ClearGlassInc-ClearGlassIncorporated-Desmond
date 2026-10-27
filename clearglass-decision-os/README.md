# ClearGlass Decision OS — v0.1.0

A separate, zero-dependency, browser-only 14-day decision-operations simulator built from the **concept** of the user-provided reference image. The visual implementation and code are original, in ClearGlass's dark graphite/crimson/teal style.

## What works

- 3 selectable synthetic mission profiles (revenue, launch, security)
- 12 selectable, keyboard-accessible dependency nodes, 17 graph edges
- Day-by-day deterministic 14-day modeled execution and controlled auto-advance/pause
- Six-task schedule and status updates
- Two explicit **simulated** human decisions affecting modeled task gates
- Emergency-stop lockout of transitions and approvals until reset
- An append-only browser-session event ledger, including resets
- Local JSON export of synthetic decisions and audit events
- Responsive/mobile layout, skip link, focus indicators, dialog, reduced motion

## Safety and truth boundary

**This is NOT a real AI orchestration backend.** Pipeline counts, signals, tasks, graph, and events are synthetic examples. `$0` is displayed for actual verified revenue; the app cannot read an inbox, fetch customers, call models, send outreach, execute commands, change repositories, process payments, or publish deployments. Approval buttons only update in-memory simulation state. No credentials, dependencies, analytics, cookies, external fonts, background requests, or persistent customer data.

Do not add production action endpoints without server-side identity, least privilege, approval-enforced execution, idempotency, immutable server-side audit, rate limiting, credential isolation, and dedicated integration tests. The UI's approval simulator is **not** security enforcement for a future backend.

## Run locally

Open `index.html` with a browser, or start `python3 -m http.server 8765 --directory .` inside this directory and visit `http://localhost:8765/`.

## Validate

```sh
node --check app.js
python3 -m unittest discover -s tests -v
```

`tests/test_static_contract.py` checks the most important file and external-capability invariants. Browser-level tests are performed separately and need an installed Chromium / Playwright environment.

## Integration / release

- Self-contained directory: `clearglass-decision-os/`; no changes to homepage, root Next.js, GitHub Actions, commerce, GitHub Pages config, Vercel project config, or existing routes.
- This folder may be served by the existing GitHub Pages static site at `/clearglass-decision-os/` **after** a reviewed merge. This is a public static demo; do **not** place private operational data in the client.
- Vercel: require a dedicated, access-protected preview project with `clearglass-decision-os` as project root and framework `Other`, if/when approved. Do not attach public production domains, use the main site's Next.js project, or assume Vercel CI is healthy.
- GitHub Actions runner billing failures prevent claiming hosted CI success; local and independently observed checks only.

## Change record

- Scope: approved standalone new system in a new directory (enhancement); no existing files modified or deleted.
- Regression risk: low pre-merge; public exposure risk if merged and demo path discovered.
- Reversal: close the PR or delete this new isolated directory on a later authorized change.
