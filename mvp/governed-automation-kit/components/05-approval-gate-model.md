# 05 — Human Approval-Gate Model

> Depends on **04 — Risk-Tiering Framework**. Score your actions first; this decides what
> the gate on each one actually looks like.
>
> A planning framework. Not legal, regulatory or security advice.

---

## The pattern

Every governed action follows the same four steps, in this order:

```
read-only analysis  →  draft  →  human approval  →  execution
```

The value is in what it forbids: **a proposal is never also an execution.** If the same
step that decides can also act, there is no gate — there is a log entry written after the
fact. Most "human-in-the-loop" automation fails here. The human is shown what already
happened.

---

## What each tier gets

| Tier | Gate | Who approves | Record |
|---|---|---|---|
| **LOW** | None | — | Log the action and its result |
| **MEDIUM** | Review after execution | Process owner, sampled or batched | Log + reviewer, reviewed within an agreed window |
| **HIGH** | **Block before execution** | Named role, not "whoever is around" | Log + approver identity + timestamp + reason |
| **CRITICAL** | **Block + second approver** | Two named roles, one accountable | Full record, retained, never overwritten |

---

## Designing one gate

```
ACTION:                  ____________________________________
TIER (from 04):          [ ] LOW  [ ] MEDIUM  [ ] HIGH  [ ] CRITICAL

WHO APPROVES
  Named role:            ____________________________________
  Backup (named):        ____________________________________
  Second approver:       ____________________________ (critical only)

WHAT THEY SEE
  [ ] What the action will do, in plain words
  [ ] The data it will change — before and after
  [ ] Why the system is proposing it
  [ ] What happens if it is wrong, and whether it can be undone
  [ ] Its risk score and tier

HOW LONG THEY HAVE
  Target response:       ______ hours
  If nobody responds:    [ ] Stays blocked (default)   [ ] Expires and is dropped
                         Never: auto-approve on timeout.

WHAT IS RECORDED
  [ ] Who approved   [ ] When   [ ] What they saw   [ ] Why   [ ] Result
```

### The timeout rule

**A gate that auto-approves when nobody answers is not a gate.** It is a delay with a
compliance story attached. If work is piling up behind a queue, the fix is a faster
approver, a lower tier, or a redesigned action — never an expiry that says yes.

---

## Six rules that make gates hold

1. **Approve actions, not sessions.** "Approved for today" re-opens everything.
2. **The approver must be able to say no** — and a no must be as easy as a yes. If
   rejecting is harder, you have built a consent button.
3. **Record the reason, not just the click.** "Approved" tells a future reader nothing.
4. **Approvals append, never overwrite.** A changed approval record is an unauditable
   one. Add a new record; leave the original.
5. **Never let a proposer approve its own proposal.** Including the automation itself.
6. **Sample what auto-executes.** Low tier means no gate, not no attention. Review a
   sample; that is how you find an action that was mis-scored.

---

## Approval fatigue — the real failure

Gates fail by being too busy far more often than by being too loose. Ten approvals a day
get read. A hundred get clicked.

When a queue is drowning, in this order:

1. **Split the action.** Most "high-risk" workflows are one risky step wrapped in four
   safe ones. Gate the step, not the wrapper.
2. **Raise the escalator threshold, not the tier.** Gate the 20%+ price changes, let the
   1% ones through.
3. **Batch the review** for medium tier — one window, many items.
4. **Only then** reconsider the tier, in writing, with a named owner.

**Never** fix a busy queue by moving an always-escalate action off the list.

---

## What to check monthly

- [ ] How many approvals were requested, and how many were rejected?
  **A rejection rate near zero means the gate is decorative** — nobody is really reading.
- [ ] Median time to approve. Rising? Fatigue is setting in.
- [ ] Any approvals granted after the target window, and why.
- [ ] Any action auto-executed that a sample says should have been gated.
- [ ] Any change to the always-escalate list — who made it, and who approved that.

---

*Planning aid only. Does not provide legal, tax, financial, compliance, or
security-certification advice. © ClearGlass Inc. Original work.*
