# Threads Growth Toolkit (compliant)

First-party automation for growing a **Threads** presence the legitimate way,
using Meta's **official Threads API**. It publishes *your own* content on *your
own* schedule and reports on *your own* analytics.

## Scope — what this does and does not do

**Does (allowed, sanctioned by Meta's API):**

- OAuth login as a single user; token exchange + refresh.
- Publish text posts to the authenticated user's own account.
- Schedule posts and publish the ones that are due.
- Read the authenticated user's own account- and post-level insights and
  produce a performance report (engagement rate, best hours, top posts).

**Does NOT (out of scope by design — these violate Meta's Platform Terms and
get accounts banned):**

- Fake/bought followers or any fake engagement.
- Mass follow / unfollow.
- Scraping other users' profiles or posts.
- Bulk / automated commenting on other people's content.
- Bypassing rate limits or platform controls.

There is no hidden switch for any of the above. Real growth here comes from
consistency and quality, which the scheduler and analytics are built to
support.

## Files

| File | Purpose |
|------|---------|
| `threads_client.py` | Typed wrapper over the official Threads Graph API (OAuth, publish, insights). Stdlib only. |
| `scheduler.py` | JSON-backed content calendar; publishes due posts idempotently. |
| `analytics.py` | Builds a performance report from your own insights. |
| `cli.py` | `profile` / `post` / `schedule` / `run-due` / `report` commands. |
| `content_calendar.example.json` | Sample queue format. |
| `tests/test_scheduler.py` | Offline tests (no network). |

## Setup

1. Create a Threads app in the [Meta developer console](https://developers.facebook.com/docs/threads)
   and complete the OAuth flow to get a **long-lived user access token**.
   `ThreadsClient.exchange_code(...)` → `exchange_for_long_lived_token(...)`
   handles the exchange; `refresh_long_lived_token()` keeps it alive.
2. Export credentials:

   ```bash
   export THREADS_ACCESS_TOKEN="<long-lived-user-token>"
   export THREADS_USER_ID="me"   # optional
   ```

3. No third-party dependencies — the client uses only the Python standard
   library. `pytest` is only needed to run the tests.

## Usage

```bash
cd threads-growth

# Who am I?
python cli.py profile

# Publish immediately
python cli.py post "Shipping something new today — here's the story…"

# Queue posts, then publish the due ones (cron this every few minutes)
python cli.py schedule "Weekly build-in-public thread" 2026-07-10T14:00:00Z --calendar content_calendar.json
python cli.py run-due --calendar content_calendar.json --dry-run   # preview
python cli.py run-due --calendar content_calendar.json             # publish

# Performance report on your own account
python cli.py report
```

## Tests

```bash
cd threads-growth
python -m pytest tests/ -q
```

The tests use a fake client and never hit the network.
