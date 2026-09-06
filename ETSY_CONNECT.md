# Connecting the Etsy shop

The control plane's Etsy surface (`app/etsy.py`, `app/routers/etsy.py`) can detect a
connection, verify it read-only, and gate every write behind human approval. What it
cannot do is *create* the connection: only Etsy can mint an access token, and only after
the shop owner approves the requested scopes in a browser. This document is that step.

Target account: **https://www.etsy.com/people/7is7jsngx568dcve** (`ETSY_PROFILE_URL`).

> A profile URL is not a credential. Etsy publishes no API that resolves a `/people/`
> handle to a shop or a token, so the URL is stored declaratively and echoed on
> `GET /etsy/connection` — it documents *which* account should be on the other end of the
> handshake, and the operator eyeballs it against the shop the token actually resolves to.

## 1. Create the Etsy app (once)

Register at <https://www.etsy.com/developers/your-apps> as the shop owner.

- Copy the **keystring** → `ETSY_KEYSTRING` (and the shared secret → `ETSY_SHARED_SECRET`).
- Register a **callback URL** and set the identical string as `ETSY_REDIRECT_URI`.
  Etsy compares it byte for byte; a trailing slash mismatch fails the exchange.
- Etsy app approval is required before the API returns live shop data.

## 2. Run the handshake

```bash
cd clearglass-commerce/control-plane
python -m app.etsy_connect --status     # what is configured, what is still missing
python -m app.etsy_connect              # the consent flow
```

The CLI prints a consent URL, you open it as the shop owner and approve, Etsy redirects
to `ETSY_REDIRECT_URI` with a `code`, and you paste **the full redirect URL** back. It
uses OAuth2 **PKCE**, so the shared secret is never transmitted and an intercepted code
is useless without the one-time verifier held in the CLI process.

Paste the whole URL, not just the code: the CLI compares the returned `state` against the
one it generated and aborts before exchanging anything if it is absent or differs. That
check is enforced in code, not left to your eyes.

Requested scopes are exactly what the operator needs, no more:

| Scope | Why |
|-------|-----|
| `listings_r` / `listings_w` | read the catalog; publish approved listings |
| `transactions_r` / `transactions_w` | read receipts; act on approved order changes |

Split across machines (browser on one, shell on another) with the verifier and state the
CLI prints:

```bash
python -m app.etsy_connect --exchange --code '<full redirect URL>' \
    --verifier '<verifier>' --state '<state>'
```

If you carry the redirect URL across, `--state` is required and verified. A bare `code`
with no `--state` is accepted only because the state was already checked on the machine
that held the browser.

## 3. Store the tokens as runtime secrets

The CLI prints `ETSY_ACCESS_TOKEN`, `ETSY_REFRESH_TOKEN` and `ETSY_SCOPES`. Put them in
the runtime secret store (Render env group, GitHub Actions secret, an uncommitted local
`.env`) — **never** in a committed file. Nothing in this flow writes a secret to disk.

Access tokens lapse after about an hour; refresh tokens last far longer:

```bash
python -m app.etsy_connect --refresh
```

A refresh carries the original grant forward and cannot widen it, so it reports the
scopes Etsy actually granted (or your stored `ETSY_SCOPES`) rather than the ones the CLI
would request — `verify_connection` reads that value to decide what the token may do, so
an overstated one would claim a capability the token lacks.

## 4. Verify

```bash
curl -sX POST localhost:8000/etsy/verify -H "Authorization: Bearer $ADMIN_API_KEY"
```

Read-only. Confirms shop identity, that listing and order permissions were granted, and
reads back listing counts as sync status; the check itself is logged to the audit ledger.
`verified: true` means the connection is live.

## What connecting does *not* unlock

Connecting grants no autonomy. Every write to the live shop —
`etsy_publish_listing`, `etsy_update_listing`, `etsy_sync_inventory`, `etsy_manage_order` —
is in `ALWAYS_ESCALATE` and scores HIGH, so the routes can only ever *queue* an approval:
they pass `execute=None` and nothing runs inline. Before connection they fail earlier
still, with `blocked_not_connected`. Publishing anything to the shop remains a deliberate
human decision recorded in the ledger.
