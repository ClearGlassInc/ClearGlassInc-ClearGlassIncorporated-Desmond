# ClearGlass Decision OS — isolated review build

**Status:** synthetic browser MVP. Not connected to real GitHub, Linear, Vercel, Stripe, email, infrastructure or databases.

## Access

Open `decision-os/index.html` on a static server, or (after a separately approved merge) `/decision-os/` on GitHub Pages. This new directory does not replace or edit the existing homepage, DELOS, routes, CI workflows, environment variables, secrets, or deployments.

## Controls

- **Run next day:** advances one of 14 synthetic sprint milestones, subject to gates.
- **Human reviews:** Day 5 (outreach plan) and Day 11 (release plan) require separate *simulated* human approvals; rejection blocks advancement until reset.
- **Pause/resume:** freezes/restores simulated progression.
- **Emergency stop:** freezes simulated progression and all review/export controls. Only explicit reset reopens a session.
- **Run log:** local session event history, persisted in editable browser localStorage. This is **not** a secure, tamper-evident audit backend.
- **JSON export:** only after explicit simulation-level report approval. Uses a local browser download, not a remote provider.
- **Command input:** `step`, `pause`, `resume`, `stop`, `reset`, `approve outreach`, `approve release`, `approve report`, `reject outreach`, `reject release`, `reject report`, `export`, `help`.

All bars, activity, metrics, graph edges, workers, data points and outcomes are **synthetic fixtures**. Manual day increments do not correspond to elapsed real days.

## Safety boundary

This is not a production authorization system. Browser approvals, localStorage and on-screen audit history can be modified by the person operating the browser. No API credentials belong in this file. For true live integration, create a separately reviewed authenticated server-side read-only bridge (GitHub/Linear/Vercel), RBAC, rate limits, durable server append-only audit, human-bound approval claims, replay protection, identity checks, and an external kill switch. No external writes before a further human authorization and validation.

## Evidence and release

- GitHub feature branch: `feature/clearglass-decision-os-mvp-20261027`.
- This commit deliberately modifies only files under `decision-os/`.
- GitHub Actions CI in this repository has a documented account billing/runner allocation blocker; no live CI pass is claimed.
- Vercel project configurations/deployments were inspected, but no deployment is triggered by this branch change unless an existing Git integration automatically previews it.
- **Manual verification:** `python3 -m http.server 8080` at the repository root, visit `http://localhost:8080/decision-os/`; test day-5/day-11 blocks, reset, pause, emergency stop, approved report export, responsive mobile layout, browser console.
- Production merge and deployment require separate release review under `AGENTS.md` and `CLAUDE.md`.

## Additional local source package

The separately delivered downloadable package contains an expanded, modular variant with a locally executed Node state-machine test; the committed GitHub review page is a standalone, dependency-free implementation of the same concepts.