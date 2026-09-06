# Cloudflare content protection

Edge protection for ClearGlass high-value content, layered **in front of** the
origin controls already shipped in the admin app (server-side premium content,
signed download tokens, per-request fingerprint/burst logging — see
`clearglass-commerce/admin/PREMIUM_PROTECTION.md`). The goal: make scraping and
republishing expensive without ever touching legitimate users or search engines.

Everything here is Terraform + one Worker, and **every enforcement rule ships in
`log` first**. You promote one tier at a time on evidence.

## What's here

| File | Purpose |
|------|---------|
| `main.tf` | Provider, verified-bot / same-site locals |
| `variables.tf` | Per-tier `action_*` knobs (default `log`), thresholds, secrets |
| `waf_rules.tf` | Custom anti-scraping rules (SEO/session allow, scraper fingerprints, datacenter crawl, hotlink) |
| `rate_limiting.tf` | Per-IP limits on premium pages, asset endpoints, and a broad-crawl burst guard |
| `managed_waf.tf` | Cloudflare Managed + OWASP rulesets (observe-first) and optional Super Bot Fight Mode |
| `logpush.tf` | Firewall-events + sampled HTTP-requests Logpush — the evidence pipeline |
| `workers/asset-guard.js` | Edge signed-token verification + hotlink prevention (mirrors `admin/lib/signing.ts`) |
| `terraform.tfvars.example` | Phase-1 (all-`log`) starting config |

```bash
cd clearglass-commerce/infra/cloudflare
cp terraform.tfvars.example terraform.tfvars   # fill in ids
export CLOUDFLARE_API_TOKEN=...                 # Zone WAF+Rulesets+Logs+Workers
terraform init && terraform plan                # review before apply
terraform apply
# Edge asset guard:
cd workers && wrangler secret put ASSET_SIGNING_SECRET && wrangler deploy
```

## How the layers fit together

```
                    ┌─────────────── Cloudflare edge ───────────────┐
request ─▶ 1. allow verified bots + logged-in sessions (SEO safe)
           2. custom WAF anti-scraping heuristics      (action = log→…)
           3. rate limiting (pages / assets / burst)   (action = log→…)
           4. managed + OWASP rulesets                 (override = log→…)
           5. asset-guard Worker: signed-token + hotlink on /api/download/*
                    └───────────────────┬───────────────────────────┘
                                        ▼
                    origin (Next.js): middleware session gate,
                    requireSession(), asset token re-check, audit log
```

The origin exposes two signed-download schemes; the edge guard handles each
appropriately:

- **`/api/download/<id>?token=…`** — the subject is inside the token, so the edge
  verifies the **same** HMAC over `assetId.exp.subject` that the origin does
  (`admin/lib/signing.ts`). Expired or asset-mismatched tokens are rejected at
  the edge and, as a backstop, again at origin.
- **`/api/assets/download?asset&expires&signature`** — the signature binds to the
  session subject, which is not present in the URL, so only the origin can verify
  it. The edge still applies hotlink protection and rate limiting; origin does the
  signature check.

## WAF rule examples (expressions)

These are the Wirefilter expressions the Terraform deploys; drop them straight
into a dashboard custom rule to prototype:

- **Preserve SEO / sessions (allow, evaluated first):**
  `(cf.client.bot) or (http.cookie contains "cg_admin_session=")`
- **Scripted-client fingerprints:**
  `http.user_agent eq "" or lower(http.user_agent) contains "python-requests" or lower(http.user_agent) contains "scrapy" or lower(http.user_agent) contains "curl/"`
- **Unverified datacenter crawl on premium routes:**
  `(<premium paths>) and not (cf.client.bot) and (cf.threat_score gt 10)`
- **Hotlink protection for assets:**
  `(<asset paths>) and not (http.referer contains "clearglass.example") and not (http.referer eq "")`
- **Rate limit (premium pages), per IP:** 60 req / 60s → mitigate 600s, counting
  only requests without the `cg_admin_session` cookie.

## Logging strategy

1. **Logpush first, always.** Before promoting anything, stream `firewall_events`
   (what matched, at what action) and sampled `http_requests` to R2/S3/Splunk
   (`logpush.tf`). While rules are in `log`, these are the *only* way to see what
   they *would* have blocked.
2. **Security Analytics** (dashboard) for fast interactive triage — pivot by ASN,
   country, user-agent, path, JA4 fingerprint, and bot score.
3. **Correlate with origin logs.** The admin app already emits structured
   `event:"admin_access"` lines with a salted request fingerprint, referrer, and
   `burst` flag. Join edge `RayID`/IP with origin fingerprints to confirm an
   actor is scraping across both layers.
4. **Alert on:** spikes in `Action=log` matches for a single rule/ASN, high
   challenge-issued counts, and origin `burst:true` — these are your promotion
   signals.

## Tuning guidance

- **Read, don't react.** Sit in `log` for ~1–2 weeks (or a full traffic cycle,
  incl. a marketing spike) per tier before promoting.
- **Whitelist reality:** confirm the verified-bot allow rule covers every
  legitimate integration (payment webhooks, uptime monitors, partner APIs) —
  add explicit `ip.src in {…}` or header allowances before you block anything.
- **Thresholds:** start generous (defaults), watch the p99 request rate of
  *known-good* users, then set limits a comfortable margin above it. Assets get a
  tighter cap than pages because real downloads are occasional.
- **OWASP:** keep the Core Ruleset at `log`/low paranoia first; anomaly scoring
  produces the most false positives. Promote only after zero legit matches.
- **Watch the challenge solve rate.** A high solve rate on a rule means humans
  are hitting it → loosen. A near-zero solve rate → safe to move to `block`.
- **One tier at a time.** Never promote two `action_*` variables in the same
  apply; you won't know which caused a regression.

## Safe rollout plan

| Phase | Action | Exit criteria |
|-------|--------|---------------|
| **0 — Baseline** | Deploy nothing enforcing. Enable Logpush + Security Analytics. Record normal rates by path/ASN/UA. | You know what "normal" looks like. |
| **1 — Observe** | Apply all rules with every `action_* = "log"` and `managed_waf_override_action = "log"`. | 1–2 weeks of data; verified-bot allow confirmed; no legit traffic in match sets. |
| **2 — Challenge gray area** | Promote highest-confidence tiers to `managed_challenge` (scraper fingerprints, hotlink). Leave rate limits + OWASP at `log`. | Challenge solve rates low; no support tickets; false-positive rate acceptable. |
| **3 — Block confirmed** | Promote confirmed-malicious tiers to `block`; rate limits → `managed_challenge`. Enable SBFM if plan supports. | Scraper volume down; clean legit traffic. |
| **4 — Tighten** | Lower `*_rpm_per_ip`, shorten windows, move rate limits to `block`, raise OWASP paranoia. | Stable steady state. |

**Rollback (any phase, seconds):** set the affected `action_*` back to `"log"`
(or `enable_managed_waf = false`) and `terraform apply` — rules keep matching for
evidence but stop acting. To fully disable, `terraform destroy` the specific
ruleset resource. The Worker can be reverted with `wrangler rollback`.

## SEO / provenance

- The verified-bot allow rule is **rule #1** in the custom phase and skips the
  rest, so Googlebot/Bingbot always reach public pages and their canonicals.
- Premium content stays server-side and auth-gated (origin), so only the minimum
  HTML is ever exposed to any client — there is no premium payload in the markup
  a scraper could lift.
- Canonical tags + structured metadata are server-rendered and untouched by the
  edge, so if content is republished the original remains identifiable.
