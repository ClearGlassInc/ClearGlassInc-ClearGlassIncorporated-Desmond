# Deployment & Operations Runbook

ClearGlass's site is a **static GitHub Pages** site (no application server) plus a
Python tooling/bots codebase validated in CI. This document is the deployment
guide, architecture overview, and incident runbook.

---

## 1. Architecture at a glance

| Layer | What | Where |
|---|---|---|
| Pages | ~28 static HTML pages | repo root (`*.html`) |
| Shared design system | tokens → theme → buttons → interactions | `tokens.css`, `theme.css`, `buttons.css`, `ui.css`, `ui.js` |
| Navigation | unified Control Surface (top cluster + command palette + drawer + mobile rail) | `control-surface.js` |
| Live data (client-side) | USGS, NWS, OpenSky, weather/AQ, FX, crypto, threat intel, GitHub Actions status | `fetch()` in page scripts |
| Tooling / bots | Python automation, health checks, agents | `bots/`, `sentinel/`, `apps/` |
| CI | tests, policy gate, security, IP scan, Pages deploy | `.github/workflows/` |

**Asset load order** (every content page): `tokens.css` (foundation) → `theme.css`
(global blue-violet layer) → `buttons.css` → `ui.css`; `control-surface.js` + `ui.js`
load deferred at end of `<body>`. The homepage (`index.html`) is the visual
reference and intentionally omits `theme.css`.

---

## 2. Local development

No build step. Serve the repo root with any static server:

```bash
python3 -m http.server 8000     # then open http://localhost:8000
```

Run the Python test suite (used by CI):

```bash
python3 -m pytest tests/ -q
```

---

## 3. Deploy

Deploys are automatic: a merge to `main` triggers the **Deploy Pages** workflow
(`.github/workflows/pages.yml`). It is the repository's only Pages artifact
producer and deployment workflow. The separate **Site Integrity Guard** validates
pull requests and pushes but cannot publish.

1. Branch from `main`, make changes.
2. Open a PR → CI runs (`CI`, `Policy Gate`, `Security`, `IP Protection`).
3. Merge (squash) once green → Pages redeploys `main`.

> **Production deployments show a red X but the site is live?** That red X is
> GitHub's *legacy* "pages build and deployment" pipeline, which keeps
> auto-running while **Settings → Pages → Source** is "Deploy from a branch".
> Its deploy step fails with `No artifacts named "github-pages"` — our own
> **Deploy GitHub Pages** workflow is the real (green) publisher. Fix it once by
> setting the source to **GitHub Actions**: run `scripts/fix_pages_source.sh`
> with an admin-scoped `GITHUB_TOKEN` (fine-grained PAT: Pages-write +
> Administration-write), or flip it in the UI. This administrative setting is
> deliberately not mutated by the deployment workflow.

**New indexable pages must be added to `sitemap.xml`** (or marked exempt in
`bots/site_health_bot.py::SITEMAP_EXEMPT`); the site-health test enforces this.

---

## 4. Rollback

Pages always serves the current `main`. To roll back:

```bash
git revert <merge-commit-sha>   # creates a clean inverse commit
git push origin main            # (via PR if main is protected)
```

GitHub Pages redeploys the reverted state automatically — typically live within
a minute or two. There is no database or stateful migration to unwind.

---

## 5. Security model (and the GitHub Pages constraint)

GitHub Pages serves static files and **cannot set custom HTTP response headers**
(no `Content-Security-Policy`, `HSTS`, `X-Frame-Options`, etc. from our side).
HTTPS itself is enforced by GitHub. Given that, our security posture is:

- **No secrets in client code.** The only "credential-ish" calls are user-supplied
  (e.g. the BYO-key advisor chat) or keyless public APIs.
- **Least-privilege CI.** Workflows default to read-only permissions; elevated
  scopes are job-scoped. Third-party actions should be pinned.
- **Untrusted input.** Live feeds and any PR/issue content are treated as
  untrusted and never `eval`'d or injected as HTML without escaping.
- **Dependency hygiene.** Keep `requirements*.txt` current; review Dependabot alerts.

> A meaningful `<meta>` CSP is **not** deployed: pages rely on inline styles/scripts
> and many cross-origin live feeds, so a strict policy would break functionality
> while a permissive one (`unsafe-inline`) adds little. Revisit if/when the site
> moves behind a CDN/edge that can set real headers.

---

## 6. Live-data feeds

All feeds run **client-side in the visitor's browser** and degrade gracefully to
an "OFFLINE"/"Status offline" state on error or rate-limit. Note: unauthenticated
`api.github.com` (Control Surface status chip) is limited to 60 req/hr per IP.

---

## 7. Incident runbook

| Symptom | Likely cause | Action |
|---|---|---|
| Site 404 / not updating | Pages build failed | Check **Deploy GitHub Pages** run; re-run; verify `.nojekyll` present |
| Production deploys red X (site still live) | Legacy "pages build and deployment" pipeline runs while Source = "Deploy from a branch" | Run `scripts/fix_pages_source.sh` (admin PAT) or set Settings → Pages → Source to "GitHub Actions" |
| Deploy run fails with `Deployment cancelled` (status was `deployment_queued`) | Several merges to `main` landed close together; the `github-pages` environment publishes one deploy at a time, so a still-queued deploy is superseded by a newer one | **Benign** — confirm the **Deploy GitHub Pages** run for a *later* commit is green (the newest successful deploy is what's served). Permanently removed by the same Source → "GitHub Actions" fix above, which stops the racing legacy pipeline. Optionally space rapid back-to-back merges |
| CI red on PR | test/lint failure | Open the failing job log; fix; the `CI` check is required to merge |
| A data panel shows OFFLINE | upstream API down / CORS / rate limit | Expected degradation; confirm endpoint health; no deploy needed |
| Status chip "Status offline" | GitHub API rate limit (60/hr/IP) | Transient; resets within the hour |
| Nav/menu missing on a page | `control-surface.js` not linked | Confirm `<script defer src="control-surface.js">` before `</body>` |
| Visual theme regression | warm color or off-token value | Re-run the warm-color scan; reference `tokens.css` |

---

## 8. Quick checklist before merge

- [ ] `python3 -m pytest tests/ -q` passes
- [ ] New pages in `sitemap.xml` (or exempt)
- [ ] Reuses shared tokens; accessible (focus, contrast, reduced-motion)
- [ ] No secrets client-side
- [ ] CI green
