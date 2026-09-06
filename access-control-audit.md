# Access-Control Audit Harness

A **defensive, authorization-focused** test harness for verifying that web/API
endpoints correctly enforce authentication and **object-level** authorization.
It targets the two most common Broken Access Control failure modes:

- **Missing authentication** — protected endpoints that respond to anonymous requests.
- **IDOR (Insecure Direct Object Reference)** — one user reaching another user's
  object by changing an identifier in the path, query, body, or cookie.

It is aligned with:

- NSA/CISA/ACSC — *Preventing Web Application Access Control Abuse* (2023).
- OWASP Web Security Testing Guide — *Testing for IDOR* (WSTG-ATHZ-04).

> ⚠️ **Authorized use only.** Run this exclusively against systems you own or have
> explicit, documented permission to test. The harness will not run until you
> assert authorization in the config, and the shipped template targets
> `example.com`, so a fresh checkout is inert by design.

## Files

| File | Purpose |
|---|---|
| `scripts/access_control_audit.py` | The harness (stdlib only — no dependencies). |
| `scripts/access_control_audit.example.json` | Config skeleton with placeholder values. |

## Quick start

```bash
# 1. Create your own scope file (never commit real tokens).
cp scripts/access_control_audit.example.json my-scope.json

# 2. Edit my-scope.json:
#    - authorization.confirmed -> true   (only with documented authorization)
#    - authorization.scope     -> what/when you may test
#    - accounts.user_a / user_b -> two real accounts at different privilege/ownership
#    - endpoints[]             -> real endpoints, marking each object's owner

# 3. Run it.
python scripts/access_control_audit.py --config my-scope.json --report findings.json
```

Regenerate a fresh skeleton at any time:

```bash
python scripts/access_control_audit.py --print-template
```

## What it checks (per endpoint)

| Check | Method | Pass condition |
|---|---|---|
| `no-auth` | request with **no** credentials | `401`/`403` (a `2xx` is a **finding**) |
| `owner` | request as the legitimate owner | records the baseline body/status |
| `cross-account` | owner's object requested as a **different** user | denied (a `2xx` is a **finding**; matching body = strong IDOR signal) |
| `id-swap` | owner requests the **adjacent** object id (`+1`) | denied unless the owner truly owns it (`2xx` = **warn**, verify manually) |

The process exits **non-zero** when any `FINDING` is present, so it can gate a
manual pipeline if you choose.

## Safety controls (by design)

- **Authorization gate** — refuses to run unless `authorization.confirmed` is
  `true` and `authorization.scope` is filled in.
- **Inert template** — placeholder hosts (`example.com`, `localhost`, …) are
  rejected unless you opt in with `settings.allow_placeholder_hosts` /
  `--allow-placeholder-hosts` (intended for a local lab).
- **Read-only default** — only `GET`/`HEAD`/`OPTIONS` are allowed. Write methods
  require `settings.allow_write_methods: true`, and even then **only the body in
  your config is ever sent** — nothing is fuzzed or generated.
- **No enumeration** — the `id-swap` check moves a single identifier by `+1`.
  There is no brute forcing or sequential scanning.
- **Throttle + hard cap** — `settings.delay_seconds` between requests and
  `settings.max_requests` total, to avoid load/DoS-like behavior.

## Config reference

```jsonc
{
  "authorization": {
    "confirmed": false,             // must be true to run
    "scope": "",                    // systems + time window you may test
    "authorized_by": ""             // engagement / ticket reference
  },
  "settings": {
    "timeout_seconds": 10,
    "delay_seconds": 1.0,           // throttle between requests
    "max_requests": 200,            // hard cap across the whole run
    "allow_write_methods": false,   // permit non-GET/HEAD/OPTIONS
    "allow_placeholder_hosts": false,
    "compare_bodies": true          // flag cross-account body matches
  },
  "accounts": {
    "user_a": { "headers": { "Authorization": "Bearer ..." }, "cookies": { "session": "..." } },
    "user_b": { "headers": { "Authorization": "Bearer ..." }, "cookies": { "session": "..." } }
  },
  "endpoints": [
    {
      "name": "Get order (path id)",
      "method": "GET",
      "url": "https://api.your-app.example/v1/orders/456",
      "owner": "user_a",            // account that legitimately owns the object
      "cross_account": "user_b",    // account that must NOT have access
      "body": null,                 // JSON body for write methods only
      "expect_owner_status": [200],
      "expect_denied_status": [401, 403, 404]
    }
  ]
}
```

### Testing body / cookie tampering

Object identifiers are often carried in JSON bodies, cookies, or headers. To test
those vectors, model each as its own endpoint entry:

- **Body** — set `method` to the real verb, `allow_write_methods: true`, and put
  the *other* user's identifier in `body`; set `owner`/`cross_account` so the
  harness sends it with each account.
- **Cookie / header** — put the identifier in the relevant account's `cookies`
  or `headers`; the cross-account run then exercises that vector directly.

## Interpreting results

A simple pass/fail rule (from the NSA/CISA advisory): **if a request succeeds only
because an object identifier changed, and the server did not independently confirm
ownership or permission, that is a finding.** Always corroborate automated findings
by reviewing the actual responses and server-side logs for the requests that
produced unexpected `200`s, plus any `403`/`404` patterns worth alerting on.

This harness is a **triage aid**, not a substitute for code review, DAST, and
manual penetration testing — which the advisory notes are needed to detect these
flaws reliably.
