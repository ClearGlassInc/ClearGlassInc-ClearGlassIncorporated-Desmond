# ClearGlass Inc. — Hardening and Threat Model

Scope: the public GitHub Pages site served from this repository, the GitHub
Actions automation that builds and audits it, and the governed backend systems
committed alongside it (`control-plane/`, `bots/`, `sentinel/`).

**Every control below is stated as a fact checkable against this repository,
with the file that implements it.** Controls that depend on GitHub or
Cloudflare account settings are listed separately in §7 as *unverifiable from
source* — they are not claimed as in place. This document deliberately makes no
assertion about the live production configuration; it describes what the
committed source enforces.

`tools/security_release_manifest.py` records a SHA-256 digest of this file in
`provenance/release-manifest.json`, so a change here is detectable.

---

## 1. Assets worth protecting

| Asset | Where | Loss scenario |
|---|---|---|
| Payment integrity | `control-plane/app/pricebook.py`, `app/routers/` | A customer is charged an attacker-chosen amount |
| Repository contents | every workflow with `contents: write` | Malicious or looping self-commits |
| Organisation credentials | 30 distinct secrets across `.github/workflows/` | Stripe, Cloudflare, Gmail, Render access |
| Audit truth | `bots/rfed_audit_bot.py`, `control-plane/app/audit.py` | A decision record is altered after the fact |
| Site integrity | root `*.html`, `_headers`, `sw.js` | Defacement, injected script, hostile redirect |
| Visitor trust | `_headers`, `legal/privacy.html` | Downgrade, framing, data leakage via referrer |

## 2. Threat actors considered

1. **Unauthenticated internet attacker** — reaches only the static site and the
   public control-plane endpoints.
2. **Malicious dependency or compromised third-party action** — the supply
   chain of `npm ci`, `pip install`, and every `uses:` step.
3. **Untrusted input reaching a model** — page text, issue bodies, fetched
   documents, and CI logs consumed by the agent layer.
4. **Over-broad automation** — the repository's own bots exceeding their
   mandate, whether through a bug or a crafted input.

An attacker who already holds an organisation owner's GitHub credentials is out
of scope; no repository-level control defends against that.

## 3. Controls at the edge (static site)

`_headers` applies to `/*`:

* `Content-Security-Policy` with `default-src 'self'`, `object-src 'none'`,
  `base-uri 'self'`, and an explicit allow-list for scripts, styles, fonts,
  frames and `connect-src`. `upgrade-insecure-requests` is set.
* `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`.
* `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`,
  `frame-ancestors 'self'`.
* `Referrer-Policy: strict-origin-when-cross-origin`.
* `Permissions-Policy: geolocation=(), microphone=(), camera=()`.
* `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, and
  `X-Permitted-Cross-Domain-Policies: none`.

**Known weakness, stated rather than hidden.** The policy carries
`script-src 'unsafe-inline'` and allows `https://cdn.jsdelivr.net` and
`https://cdnjs.cloudflare.com`. Inline script execution is therefore not
blocked by CSP, and a compromise of either CDN would execute in the site's
origin. The site's pages embed inline `<style>` and `<script>` extensively, so
removing `'unsafe-inline'` requires either nonces (which GitHub Pages cannot
generate per-response) or extracting every inline block. This is the single
largest outstanding hardening item for the static site.

`form-action` is restricted to `'self'`, Formspree and FormSubmit — the two
form handlers the site actually posts to.

RFC 9116 contact is served from `/.well-known/security.txt`, with the
`Content-Type` pinned in `_headers` so it renders as plain text.

## 4. Controls in CI/CD

Verifiable by running `python3 scripts/audit_github_actions.py`, which exits
non-zero on any error and is the gate described here:

* **Every external action is pinned to a full 40-character commit SHA** — 239
  of 239 `uses:` references across the 74 registered workflows. A tag pin is a
  hard error, not a warning, because a tag can be repointed by its owner.
* **Every workflow declares top-level `permissions:`** — 74 of 74. The default
  read/write token is never inherited implicitly.
* **Checkout credentials are dropped by default.** 95 checkout steps set
  `persist-credentials: false`; a job that leaves them enabled is reported.
* **Unattended jobs that push repository content must name a protected
  `environment:`.** The auditor raises `GOVERNANCE:` on any job combining
  `contents: write` with a `git push` and no environment. `automation-write` is
  the environment used for these (8 workflows).
* **Secrets are never interpolated into `run:` blocks** where the auditor can
  detect it; they are passed through `env:`.
* Local composite actions live in `.github/actions/` and are audited with the
  same rules, including their nested `uses:` steps.

The auditor is offline and fail-closed: it never calls the GitHub API and never
executes a workflow, so it cannot be defeated by network conditions.

## 5. Controls in the governed backends

The invariant shared by both systems is **read-only analysis → draft → human
approval → execution.**

**Commerce control plane** (`control-plane/`):

* `app/governance.py` scores every proposed action 0–100. Pricing, payment,
  tax, refund, fulfilment, reorders and mass outbound are blocked until an
  `approvals` row reaches `approved`.
* **Prices are resolved server-side.** `POST /checkout/session` accepts SKUs
  and quantities only; amounts come from `app/pricebook.json`, never the
  request body, because a line item's amount becomes Stripe's `unit_amount`.
  `tests/test_pricebook.py` asserts the request schema is exactly
  `{sku, quantity}`.
* Mutating admin routes require `Authorization: Bearer` (`app/security.py`).
  `APP_ENV=production` with no `ADMIN_API_KEY` **fails closed at startup**.
  `tests/test_route_auth_coverage.py` asserts every mutating route is gated.
* The Stripe webhook is signature-verified and idempotent on redelivery via
  `orders.external_ref`. Checkout, the webhook and approval decisions carry
  per-IP rate limits.
* Every material change is appended to a tamper-evident `events` ledger.

**RFED audit trail** (`bots/rfed_audit_bot.py`):

* Each action is recorded Request → Facts → Evidence → Decision and sealed into
  a SHA-256 hash chain, so altering a past record breaks every later link.
* Actions touching access, credentials, remote execution or data export score
  92–100 and always escalate. `modify_audit_log` is blocked outright. **Unknown
  actions fail closed at 85.**
* Ungrounded output, low confidence, and injection markers in untrusted facts
  each hard-gate independently.
* Approvals append a new record; they never mutate the original.
* `tests/test_rfed_hash_parity.py` pins the Python and n8n implementations to
  byte-identical canonical JSON and identical chain hashes.

## 6. Prompt-injection posture

Untrusted text reaches the agent layer through page content, issue and PR
bodies, and CI logs. The controls that matter are that a model's *conclusion*
never becomes an *action*: every externally-influenced action routes through
the same approval gate as a human-proposed one, and injection markers in
untrusted facts are themselves a gating condition in the RFED risk table. A
successful injection can therefore corrupt a draft or a recommendation; it
cannot by itself move money, change access, or push code.

## 7. Not verifiable from this repository

These are **not** claimed as in place. Each requires an authorised
administrator to confirm in the GitHub or Cloudflare console:

* Runtime values and rotation state of all 30 workflow secrets.
* Whether the `automation-write` environment actually has required reviewers
  configured. Naming an environment is necessary but not sufficient — an
  environment with no protection rules gates nothing.
* Branch protection, required status checks, and who can dispatch workflows.
* Whether GitHub Actions is entitled to run at all. As of the last audit no
  user-authored workflow had ever completed with non-zero
  `billable.UBUNTU.total_ms`; a green check on this repository is not evidence
  a job executed.
* Pages deployment source (branch mode vs. GitHub Actions) — `pages.yml` uses
  `actions/deploy-pages`, which requires the latter.
* Cloudflare Worker routes and DNS. Three Workers are deployed; no committed
  `wrangler.toml` corresponds to any of them.
* Any WAF, rate limiting or bot management at the edge.

## 8. Outstanding hardening items

| # | Item | Severity |
|---|---|---|
| H1 | `script-src 'unsafe-inline'` in the site CSP (§3) | High |
| H2 | Two CDNs in `script-src` widen the supply chain to third-party hosts | Medium |
| H3 | Deployed Cloudflare Workers have no committed, reproducible config | Medium |
| H4 | `sharp` carries two unfixed high advisories (libvips/libheif) | Medium |
| H5 | `automation-write` protection rules unverified (§7) | Medium |

## 9. Reporting

Report vulnerabilities privately per `SECURITY.md` and
`/.well-known/security.txt`. Do not open a public issue for suspected
vulnerabilities, secrets, authentication bypasses, or exploit details.
