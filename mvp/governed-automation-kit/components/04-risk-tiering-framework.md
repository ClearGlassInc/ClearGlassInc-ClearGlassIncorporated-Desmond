# 04 — Automation Risk-Tiering Framework

> **What this is.** A method for deciding how much human oversight an automated action
> needs, *before* you build it. It is generalised from a governed automation system
> ClearGlass built and runs, not written for a template.
>
> **What it is not.** It is not legal, regulatory or security advice, and it does not make
> any system compliant, secure or certified. It is a planning framework.

---

## The idea in one line

**Score the action, not the tool.** "Is AI safe?" has no answer. "Can this action move
money, and can we undo it?" has one, and that answer decides the oversight.

---

## Step 1 — Score each action 0–100

Take every action your automation could *take* — not every feature it has. Score each on
its base risk, then apply the escalators.

### Base scores

| Band | Score | What belongs here |
|---|---|---|
| **Read / draft** | 0–15 | Reading data, generating a draft nobody has sent, checking status, running a report |
| **Internal write** | 20–45 | Updating your own records, importing a catalogue, publishing internal content, reversible customer-visible edits |
| **External / financial** | 60–88 | Changing prices, sending outbound at scale, writing to a live marketplace, capturing a payment, placing a supplier order |
| **Irreversible / platform** | 90–100 | Refunds, payment settings, tax settings, fulfillment rules, anything that cannot be undone or that changes how money moves |

**An action you have not scored is not low risk.** Score it 85 and gate it until someone
decides otherwise. Unknown must fail closed, or the framework leaks exactly where it
matters — at the action nobody thought about.

### Escalators — add to the base score

| Signal | Add | Why |
|---|---|---|
| Changes an amount or price by more than 20% | +10 | The blast radius of a fat finger scales with the delta |
| Affects all customers, or is a bulk operation | +8 | One bad decision, multiplied |
| The system is uncertain, or data is missing | +12 | Low confidence is itself a reason to stop |

**Low confidence hard-gates on its own.** Do not let it merely bump a score — a +12 on a
base of 15 still lands in the low tier and would auto-execute, which is the opposite of
what the signal is telling you. If the system is unsure, a human looks. Always.

---

## Step 2 — Read the tier off the score

| Tier | Score | What happens |
|---|---|---|
| **LOW** | 0–29 | Auto-execute, and log it |
| **MEDIUM** | 30–59 | Execute, queue for review |
| **HIGH** | 60–89 | **Blocked** until a human approves |
| **CRITICAL** | 90–100 | **Blocked**, approved with the highest scrutiny |

---

## Step 3 — Apply the always-escalate override

Some actions are gated regardless of score, because the score is not the point — the
category is. Score drift, a config change or an optimistic assessment must never be able
to open these:

- Changing live pricing
- Payment, tax or fulfillment settings
- Refunds and payment capture
- Reordering inventory or placing a supplier order that spends money
- Any write to a live external marketplace (listings, stock, orders)
- Mass outbound communication

**Write your own list in the worksheet below and treat it as fixed.** The override exists
precisely so that nobody has to re-argue it under time pressure.

---

## Step 4 — Worksheet

Copy one block per action.

```
ACTION:                    ______________________________________
What it does:              ______________________________________
Can it be undone?          [ ] Yes, instantly  [ ] Yes, with effort  [ ] No
Does it move money?        [ ] No  [ ] Indirectly  [ ] Yes
Does a customer see it?    [ ] No  [ ] Internally  [ ] Yes, immediately
Touches personal data?     [ ] No  [ ] Yes  →  review before scoring

BASE SCORE:                ______ / 100
  + >20% amount change     ______
  + bulk / all customers   ______
  + low confidence         ______
TOTAL:                     ______

TIER:                      [ ] LOW  [ ] MEDIUM  [ ] HIGH  [ ] CRITICAL
On the always-escalate list? [ ] No  [ ] Yes  →  gate it regardless of tier

DECISION:                  [ ] Auto-execute + log
                           [ ] Execute + queue for review
                           [ ] Block until approved by: ______________
OWNER:                     ______________________________________
```

---

## Worked example

A marketing automation that "sends campaigns" is not one action. Split it, and the
oversight falls out on its own:

| Action | Base | Escalators | Total | Tier | Decision |
|---|---|---|---|---|---|
| Draft campaign copy | 20 | — | 20 | LOW | Auto-execute + log |
| Update the audience segment | 40 | — | 40 | MEDIUM | Execute, review after |
| Send to the full list | 78 | +8 bulk | 86 | HIGH | **Blocked** — human approves |
| Change the offer price in it | 80 | +10 delta | 90 | CRITICAL | **Blocked** + always-escalate |

One tool. Four different answers. This is the whole value of scoring actions rather than
systems: three quarters of it runs unattended, and the quarter that can embarrass you
does not.

---

## Three failure modes this is designed to prevent

1. **Tool-level approval.** Approving "the AI agent" approves every action it will ever
   take, including the ones added next quarter. Approve actions.
2. **Fail-open on the unknown.** A new action nobody scored slips through as low risk.
   Default it to 85.
3. **Silent tier drift.** A gated action is quietly rescored to avoid the queue.
   The always-escalate list is the defence; keep it in review, not in config.

---

## How this connects to the rest of the kit

- The tier you land on drives the oversight design in **05 — Human Approval-Gate Model**.
- It drives the ranking in **03 — Automation Prioritization Matrix**.
- It changes the economics in **09 — the ROI calculator**: a gated action keeps a
  permanent human review cost, so it returns less than the hours it appears to remove.
  Run the calculator before committing — some high-tier workflows come back as
  *don't automate this*, and that is a finding, not a failure.

---

*This framework is a planning aid. It does not provide legal, tax, financial,
compliance, or security-certification advice, and it does not make any system compliant
or secure. © ClearGlass Inc. Original work.*
