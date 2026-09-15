# Automation policy

What the repository's own automation may change, and when.

This is not advisory. The rules below are implemented in
`scripts/automation_governance.py` and asserted in
`tests/test_automation_governance.py`; a policy that lives only in a document is
one that stops being true the first time someone is in a hurry.

```bash
python3 scripts/automation_governance.py --self-check        # do the invariants still hold?
python3 scripts/automation_governance.py --paths <files...>  # may a bot merge this change?
python3 scripts/automation_governance.py --state state.json  # is the repo healthy enough to change?
```

Exit code is the contract: **non-zero means do not proceed.**

## The three tiers

| Class | Examples | What automation may do |
|---|---|---|
| **LOW** | Documentation, tests, generated reports under `operations/` | Open a PR, run the full suite, auto-merge once every required check passes **and** the circuit breakers allow it |
| **MEDIUM** | Application logic, non-payment API routes, performance work, anything not on the allow-list | Open a PR. Human approval required |
| **HIGH** | Payments, webhooks, checkout, pricing, auth, workflows, migrations, dependencies, infrastructure, published legal text | Open a PR. Human approval required. **Never** auto-merged, however small the diff |

Two properties of the classifier worth knowing before relying on it:

- **A change is only as safe as its riskiest file.** One protected path in an
  otherwise-trivial diff makes the whole change HIGH. Changes merge as a unit.
- **Unrecognised is MEDIUM, not LOW.** A path the policy has never seen needs a
  human. An empty change — something reporting that it touches nothing — is
  refused outright, because a broken caller is not evidence of safety.

Protected paths are listed in `PROTECTED_PATHS`, and `PROTECTED_NAME_MARKERS`
catches payment/auth/migration code by filename wherever it lives, so a new
module is protected the day it is added rather than the day someone remembers to
extend the table.

## Circuit breakers

Classification answers "is this change small enough". The breakers answer "is
the system healthy enough to be changing itself right now". Both must pass.

| Breaker | Limit | Effect when tripped |
|---|---|---|
| Auto-merges per day | 1 | No further auto-merge that day |
| Open bot pull requests | 3 | No further auto-merge |
| Consecutive failed deployments | 2 | **All** mutation halts |
| Secret scan red | — | **All** mutation halts |
| Critical vulnerability scan red | — | **All** mutation halts |
| Payment tests red | — | **All** mutation halts |
| Production health red | — | **All** mutation halts |
| Webhook verification / order, inventory or fulfillment reconciliation red | — | Revenue-side automation halts |

**Every health signal defaults to failing when absent.** "We did not check" and
"the check failed" are the same answer to a system deciding whether to change
itself unattended. This is deliberately inconvenient: the usual way a breaker
stops working is that the signal feeding it quietly disappears and the breaker
reads the absence as fine.

The daily auto-merge limit is about attribution rather than volume — when
something breaks, one automated change per day can be correlated with it by eye.

## What no automation may do

- Force-push, rewrite history, or push to a protected branch directly.
- Disable a branch protection, a required check, or a test. A failing test is
  fixed or the change is abandoned; it is never skipped or quarantined.
- Merge its own change to a payment, auth, workflow, migration, dependency,
  infrastructure or published-legal path.
- Change live prices, issue refunds, publish or reprice an Etsy listing, send
  marketing email, or move money. These are always-escalate actions in
  `control-plane/app/governance.py` and are gated in code, not by convention.
- Fulfill an order from a browser success page or a client-side callback.
  Fulfillment follows a verified server-side webhook, or it does not happen.

## Standing caveat: CI currently reports nothing

Since 2026-09-06 GitHub Actions has not been dispatching runners for this
organisation (`PRODUCTION-RECOVERY.md` §1.1). Jobs fail in seconds with no
retrievable logs, which means **a green check is the absence of signal, not
success.** Until that is fixed in organisation settings, run the gates locally
before pushing:

```bash
pip install pytest pytest-cov pyyaml "ruff==0.15.8"
python3 scripts/ci_local.py
```

This has a direct consequence for the policy above: the breakers read CI
results, and CI results are currently unavailable. That is why the absent-signal
default is "failing" — in the current state of the repository, the honest output
of `evaluate_breakers` is *halted*, and it is.

## Changing this policy

Bump `POLICY_VERSION` in `scripts/automation_governance.py` when the tables or
gating logic change, so an audit record says which policy produced it. Run
`--self-check`; it fails loudly if the policy has been edited into no longer
refusing what it claims to refuse.
