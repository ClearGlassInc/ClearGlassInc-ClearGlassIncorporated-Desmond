# Deploying www.clearglassinc.com on Cloudflare Pages

Runbook for moving the static site off GitHub Pages. **Nothing here needs
GitHub Actions or GitHub billing** — Cloudflare builds and serves independently.

## Why

GitHub Actions has executed no job since **2026-09-06T13:14:52Z**. The failures
are pre-execution: `runner_id: 0`, no `steps` array, `billable.UBUNTU.total_ms: 0`,
confirmed on every head since. Because the built-in `pages build and deployment`
workflow is the current deploy mechanism, production has been frozen at the
2026-09-06 content that whole time, while four sets of changes merged to `main`
behind it. Evidence: `PRODUCTION-RECOVERY.md` §1.1 and §1.2.

Restoring Actions entitlement is still worth doing — it is what CI needs. This
path is about getting the site itself live without waiting for it.

## What gets published

`tools/build_pages.py` — the site's own **fail-closed** publisher. It allowlists
public file extensions and denies source trees by name, so `bots/`, `tests/`,
`scripts/`, `sentinel/`, `tools/`, `percival_v9/`, `customer-profiles/` and
`operations/` never reach the bundle. `deployment/cloudflare-pages/build.sh`
wraps it and refuses to publish if a required file is missing or a denied tree
leaks in.

Measured on `ba5fb80`: **475 files, 158 HTML pages, 32 MB**, largest single file
2.66 MiB. Against Cloudflare Pages limits (20,000 files, 25 MiB per file,
100 `_headers` rules, 2,000 chars per header) the bundle uses 4 rule blocks and
a 695-character CSP. Comfortably clear on every axis.

### Two things improve the moment this goes live

* **`_headers` starts working.** GitHub Pages has no support for a `_headers`
  file, so the CSP, HSTS, `X-Frame-Options`, `Referrer-Policy` and
  `Permissions-Policy` this repo has been carrying are **inert in production
  today**. Cloudflare Pages parses `_headers` from the output directory and its
  rules override the defaults, so they take effect on the first deploy.
* **Source stops being served.** GitHub Pages in "deploy from a branch" mode
  serves the branch root, so every committed file is reachable over HTTP. This
  bundle serves only the built output. **UNVERIFIED from the audit environment**
  (outbound to the live host is blocked by its proxy) — check it yourself in one
  line, and if either returns 200 that is the exposure this closes:

  ```
  curl -o /dev/null -w '%{http_code}\n' https://www.clearglassinc.com/bots/marketing_bot.py
  curl -o /dev/null -w '%{http_code}\n' https://www.clearglassinc.com/PRODUCTION-RECOVERY.md
  ```

## Path A — Git integration (recommended)

Auto-deploys on every push to `main`, with no GitHub Actions involvement.
Cloudflare clones the repo and builds on its own infrastructure.

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** →
   **Connect to Git** → select `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`.
2. Build settings:

   | Setting | Value |
   |---|---|
   | Production branch | `main` |
   | Framework preset | None |
   | Build command | `deployment/cloudflare-pages/build.sh` |
   | Build output directory | `dist` |
   | Root directory | *(leave empty)* |

3. Save and deploy. Verify on the `*.pages.dev` URL it gives you **before**
   touching DNS.

The build command is `python3`-only and installs nothing. If Cloudflare's build
image turns out not to ship Python 3, the build will fail at step 3 with a
`python3: not found` — that costs nothing, breaks nothing, and Path B is the
answer. (Whether that image includes Python was not confirmable from the audit
environment, so treat A as "try first", not "guaranteed".)

## Path B — direct upload (guaranteed, no build image dependency)

Build locally, upload the finished bundle. Needs a Cloudflare API token with
**Account → Cloudflare Pages → Edit**.

```bash
deployment/cloudflare-pages/build.sh          # -> ./dist, with its own guards
npx wrangler pages project create clearglass-site --production-branch main
npx wrangler pages deploy dist --project-name clearglass-site
```

Trade-off: no auto-deploy. Re-run both commands after any change to the site.

## The DNS cutover — do this last

Both paths give a working `*.pages.dev` URL first. Only cut over once you have
loaded that URL and are satisfied.

1. Pages project → **Custom domains** → **Set up a custom domain** →
   `www.clearglassinc.com`. Cloudflare provisions the certificate.
2. It will tell you the DNS record to change. In the `clearglassinc.com` zone,
   repoint `www` from the GitHub Pages target to the Pages project.
3. Leave the GitHub Pages configuration **in place and untouched** until you are
   satisfied. It costs nothing to leave, and it is the rollback.

Verify after propagation:

```bash
curl -sI https://www.clearglassinc.com/ | grep -iE 'server|content-security-policy|strict-transport'
curl -o /dev/null -w '%{http_code}\n' https://www.clearglassinc.com/.well-known/security.txt
```

Expect a Cloudflare `server` header, the CSP and HSTS from `_headers` now
present, and `200` on `security.txt` (it 404s today — the dot-directory was
stripped by the original repository upload and restored in `88470b1`).

## Rollback

| Step | Undo |
|---|---|
| DNS cutover | Repoint `www` back to the GitHub Pages target. This is why step 3 above leaves GitHub Pages configured. Propagation-bound, no rebuild. |
| A bad Pages deploy | Pages keeps every deployment. **Deployments** → pick the previous one → **Rollback**. Instant, no DNS change. |
| The whole move | Repoint DNS, then delete the Pages project. The repository is unchanged either way — this runbook adds files, it modifies nothing the site serves. |

## Verified before writing this

Against the bundle built from `ba5fb80`, served locally and driven in
Chromium 141 with `tools/browser/verify_motion.py`:

```
39/39 checks passed
CLS at load                 0.0213
atmosphere renderer         webgl2
reduced motion              static SVG substituted, no canvas, content visible
JavaScript disabled         hero, sections and CTA all reachable
mobile 390 + touch, 400px   no page errors, no horizontal overflow
```

Exclusions confirmed by request against the same bundle: `/bots/marketing_bot.py`,
`/PRODUCTION-RECOVERY.md` and `/tests/test_seo_audit.py` all **404**, while
`/.well-known/security.txt` returns **200**.

## Known wart

72 dated files like `20260515T152813.json` publish from the repository root.
They are internal marketing narrative-generation reports — `run_utc`,
`prompt_source`, `total_audiences`, `output_dir`, `narratives`. No credentials,
checked. They are noise rather than a breach, but they expose internal prompt
sources and output paths and there is no reason for them to be on the website.
Add them to `DENIED_NAMES` in `tools/build_pages.py`, or move them under a
denied tree, whenever convenient. Not a blocker for the cutover.
