# Premium route protection (admin cockpit)

Ensures premium content — operator copy, workflows, and agent prompts — is
**never fully served to an unauthenticated visitor**. Protection is enforced
server-side (middleware + SSR + protected APIs), so nothing sensitive reaches
the browser before auth. No client-side blocking is used, so screen readers,
keyboard navigation, and form inputs are unaffected.

This layer is complementary to — not a replacement for — the control plane's own
`ADMIN_API_KEY` gate (`control-plane/app/security.py`), which independently
guards every mutating commerce endpoint.

## What each piece does

| File | Role |
|------|------|
| `middleware.ts` | Edge front door. Fingerprints + logs every request, lets a public allowlist through, and requires a valid session cookie for everything else — redirect to `/login` for pages, `401` for `/api/*`. Adds `no-store` + `noindex` + hardening headers. |
| `lib/auth.ts` | Edge-safe HMAC-SHA256 session tokens (mint/verify). No deps, no Node built-ins, so it runs in middleware. |
| `lib/session.ts` | Server-only `getSession()` / `requireSession()` for SSR pages + route handlers (defense-in-depth backstop). |
| `lib/signing.ts` | Signed, expiring download tokens bound to a specific asset id. |
| `lib/logging.ts` | Request fingerprint (salted hash of ip+ua), referrer, timestamp, and in-instance burst detection → one structured JSON log line per request. |
| `lib/premium.ts` | Server-only premium content. Never imported by a client component, so it stays out of the browser bundle. |
| `app/login/page.tsx` | Accessible, no-JS `<form>` login (labelled input, `role="alert"` errors, natural tab order). |
| `app/api/auth/login` / `logout` | Exchange password → httpOnly/Secure/SameSite session cookie; clear it. Fails closed in prod without config. |
| `app/playbooks/page.tsx` | **Authenticated SSR** example — premium copy/workflows/prompts rendered entirely server-side, with per-asset signed download links. |
| `app/api/premium/route.ts` | **Protected API** example — premium JSON only for a valid session. |
| `app/api/download/[asset]/route.ts` | Serves an asset only when session **and** a valid, unexpired, asset-bound token are present. |

## Request flow

```
request ─▶ middleware ─▶ fingerprint + log + burst check
                       ├─ public path? ─▶ allow (hardened headers)
                       └─ session cookie valid?
                             ├─ no  ─▶ page: 307 → /login?next=…   api: 401
                             └─ yes ─▶ render SSR / run handler
                                          └─ requireSession()/getSession() re-check
```

## Accessibility guarantees

- Protection is **server-side only** — no overlay, focus trap, or JS gate that a
  screen reader or keyboard user could get stuck behind.
- Login is a native `<form>` that works with JavaScript disabled; every field
  has a `<label>`, errors use `role="alert"`, and a "Skip to main content" link
  is the first focusable element in the layout.
- Sign-out and downloads are plain form/link navigations — no client blocking.

## SEO / provenance (kept on every page)

- Canonical URLs via `metadata.alternates.canonical` (+ `metadataBase`).
- `robots: noindex, nofollow` and `X-Robots-Tag: noindex` header (admin is
  private and must not be indexed).
- Visible copyright in the footer **and** machine-readable `copyright` meta on
  every page.

---

## Deployment checklist

**Secrets (required in production — auth fails closed without them):**

- [ ] `AUTH_SECRET` — ≥ 16 chars, `openssl rand -hex 32`. Signs session cookies.
- [ ] `ADMIN_DASHBOARD_PASSWORD` — the operator login password.
- [ ] `APP_ENV=production` — enables `Secure` cookies + fail-closed login.
- [ ] `ASSET_SIGNING_SECRET` (optional) — rotate download-link signing
      independently of sessions; falls back to `AUTH_SECRET`.
- [ ] `LOG_SALT` (optional) — salt for fingerprint hashing.
- [ ] `NEXT_PUBLIC_SITE_URL` — absolute origin so canonical tags resolve.
- [ ] Store all of the above in the platform's secret manager (Render env group
      / Docker secrets). Do **not** commit them. `.env.example` documents them.

**Transport & cookies:**

- [ ] Serve over HTTPS only — session + download cookies are `Secure` in prod.
- [ ] Confirm the platform forwards `X-Forwarded-For` so fingerprints/logs see
      the real client IP.

**Verify after deploy (all should hold):**

- [ ] `GET /playbooks` while logged out → `307` to `/login`.
- [ ] `GET /api/premium` while logged out → `401`.
- [ ] Wrong password → back to `/login?error=1`; correct → session cookie set
      (`HttpOnly; Secure; SameSite=Lax`).
- [ ] Authenticated `/playbooks` renders; download link works once, then `403`
      after ~5 min (token expiry).
- [ ] A tampered download token → `403`; a token minted for asset A cannot fetch
      asset B.
- [ ] `view-source` of `/login` contains no premium copy/prompts.
- [ ] `GET /healthz` → `200` without a session (for uptime monitors).

**Logging & alerting:**

- [ ] Ship stdout to a log drain; parse the `event:"admin_access"` JSON lines.
- [ ] Alert on `level:"warn"` (blocked requests) and `burst:true` spikes.
- [ ] Note: burst detection is **per instance** and in-memory. For a global
      limit across replicas, back it with a shared store (Redis/Upstash) or rely
      on the control-plane rate limits / a CDN/WAF rule. Tune `BURST_THRESHOLD`.

**Hardening (already applied, confirm not overridden by the platform):**

- [ ] `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
      `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`
      on protected responses.

> Next 16 note: the framework now prefers the `proxy.ts` filename over
> `middleware.ts` (build logs a deprecation notice). The current `middleware.ts`
> still works and is picked up as the proxy; rename the file and its exported
> function to `proxy` when convenient — the logic is unchanged.
