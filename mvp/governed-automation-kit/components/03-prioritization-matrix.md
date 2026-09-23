# 03 — Automation Prioritization Matrix

> Ranks the candidates from **01/02**. Uses risk tiers from **04** and payback from
> **09**. Produces a defensible order, not a gut feel.
>
> A planning aid. Not legal, tax, financial, compliance or security advice.

---

## Score each candidate

Six factors, 1–5 each. Score honestly — the matrix is only useful if it can tell you your
favourite idea should wait.

### Impact — what it is worth

| | 1 | 3 | 5 |
|---|---|---|---|
| **Time recovered** | < 2 h/month | 2–20 h/month | > 20 h/month |
| **Error reduction** | Rare, cosmetic | Occasional, costly to fix | Frequent, customer-visible |
| **Strategic value** | Convenience | Removes a bottleneck | Removes a key-person or continuity risk |

### Cost — what it takes

| | 1 (cheap) | 3 | 5 (expensive) |
|---|---|---|---|
| **Build effort** | Days | Weeks | Months |
| **Dependency risk** | Systems we control, documented APIs | Mixed | No API, or a vendor we cannot influence |
| **Change exposure** | Stable for years | Changes occasionally | Changes every quarter |

```
CANDIDATE: ______________________    (WF-____)

IMPACT      Time ___  Errors ___  Strategic ___     →  Impact total ___ /15
COST        Build ___  Dependency ___  Change ___   →  Cost total   ___ /15

RISK TIER (from 04):  [ ] LOW  [ ] MEDIUM  [ ] HIGH  [ ] CRITICAL
PAYBACK (from 09):    ______ months   Verdict: ______________________
DOCUMENTED (from 02): [ ] Fully  [ ] Partly  [ ] No
OWNER NAMED:          [ ] Yes  [ ] No

PRIORITY SCORE = Impact − Cost = ______
```

---

## Then apply the three overrides

The arithmetic gets you a shortlist. These three decide the order, and each one outranks
the score:

**1. Not documented → not eligible.** Regardless of score. Send it back to 02.
You cannot automate a process you cannot describe; you can only automate your assumptions
about it.

**2. No named owner → not eligible.** Regardless of score. Automation with no owner
becomes unattended automation, then unexplained automation, then an incident.

**3. The calculator's verdict outranks the priority score.** A `DO_NOT_AUTOMATE` from 09
means the gate and upkeep cost more than the manual work. A high impact score does not
change that — it just means you are losing more, faster.

---

## Place what survives

| | **Low / Medium risk** | **High / Critical risk** |
|---|---|---|
| **High impact, low cost** | **Do first.** Quick wins that build the case for the rest. | **Do carefully.** Real value, but design the gate (05) before writing any code. |
| **High impact, high cost** | **Plan properly.** Scope it, stage it, get a budget. | **Scrutinise.** The most expensive way to fail. Pilot on a slice first; prove the gate works before scaling. |
| **Low impact, low cost** | **Batch them.** Cheap enough to do together when convenient. | **Skip.** The oversight costs more than the benefit. |
| **Low impact, high cost** | **Don't.** | **Don't.** |

---

## Ranked plan

| Rank | Candidate | Impact | Cost | Score | Tier | Payback | Verdict (09) | Eligible? | Decision |
|---|---|---|---|---|---|---|---|---|---|
| 1 | | /15 | /15 | | | mo | | | |
| 2 | | /15 | /15 | | | mo | | | |
| 3 | | /15 | /15 | | | mo | | | |

**Do not start more than two at once.** The constraint on automation programmes is almost
never ideas — it is the attention of whoever has to review, approve, and fix them. That
person is already doing another job.

---

## Re-run this quarterly

Scores decay. A process that changed, a system that lost its API, a person who left — any
of these move a candidate. Re-scoring four items takes twenty minutes and is the
difference between a plan and a list of things you meant to do.

Keep the rejected ones with their reasons. The note is what stops the same idea being
re-proposed as if it were new.

---

*© ClearGlass Inc. Original work. Planning aid only; no guarantee of savings,
compliance, performance or business outcomes.*
