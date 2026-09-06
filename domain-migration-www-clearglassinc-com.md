# Domain Migration — `www.clearglassinc.com`

Record of the migration of the site's canonical web domain to
`www.clearglassinc.com`, and the post-merge verification that confirmed it is
production-safe.

## Scope

All public-facing web references across the repository were standardized to the
single canonical host **`www.clearglassinc.com`** — HTML pages, `sitemap.xml`,
`robots.txt`, `llms.txt`, `schema.json`, marketing/SEO assets, agent prompts,
corporate & legal docs, `CNAME`, and the site-reliability audit config.

### Migration rules applied

| Source | Rewritten to |
|--------|--------------|
| `https://clearglassinc.github.io/…` (Pages web URLs) | `https://www.clearglassinc.com/…` |
| `clearglassinc.ca` (web) | `www.clearglassinc.com` |
| bare `clearglassinc.com` (web) | `www.clearglassinc.com` |
| `CNAME` | `www.clearglassinc.com` |
| `@clearglassinc.ca` (email) | `@clearglassinc.com` |

### Intentionally preserved (NOT rewritten)

- **GitHub repository identifiers** — `owner/clearglassinc.github.io` slugs and
  `github.com/ClearGlassInc/ClearGlassInc.github.io` clone/repo URLs. These name
  the repository, not the website.
- **`api.clearglassinc.com`** — the distinct API subdomain (sibling of the site
  on the same root domain).
- **Email mail domain** — addresses stay on `clearglassinc.com`; `www.` is a web
  host prefix and is never added to mail addresses.

## Verification (post-merge, on `main`)

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `python -m pytest tests/` | 568 passed, 4 skipped |
| `python scripts/site_reliability_audit.py` | 0 errors, 0 warnings |
| `python scripts/store_sync.py --check` | catalog in sync |
| `python scripts/workflow_doctor.py` | clean |

Contract/security checks: single canonical host across `sitemap.xml` and the
`index.html` canonical tag; repo slugs and the `api.` subdomain intact; no stray
`.ca`/bare-web `.com`; no malformed hosts; no secrets in the changed files.

## Operational follow-ups (outside the repo)

1. **DNS + GitHub Pages HTTPS** — confirm DNS points `www.clearglassinc.com` at
   GitHub Pages and that HTTPS is provisioned in Settings → Pages.
2. **Plausible analytics** — `analytics.js` reports the domain as
   `www.clearglassinc.com`; ensure a matching site exists in the Plausible
   dashboard.
3. **Cert monitoring** — the cert bot now watches `www.clearglassinc.com` in
   strict mode (a custom-domain cert expiry is a real outage), which is intended.
