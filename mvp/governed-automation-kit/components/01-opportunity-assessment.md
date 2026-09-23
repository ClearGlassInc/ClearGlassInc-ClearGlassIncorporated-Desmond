# 01 — Automation Opportunity Assessment

> Start here. This finds the candidates; **02** documents them, **03** ranks them,
> **04** scores their risk, **09** prices them.
>
> A planning aid. Not legal, tax, financial, compliance or security advice.

---

## Before you look for opportunities

Two questions kill more bad automation projects than any tool review:

1. **Does anyone actually want this to change?** Automating a process whose owner likes
   it as it is produces a working system nobody uses.
2. **Would you pay a person to do this?** If the task is not worth a salaried hour, it is
   not worth an implementation and a maintenance commitment either.

If either answer is no, stop. That is a successful assessment.

---

## Find the friction

Work through each area and write down what people actually complain about. Complaints are
better data than process diagrams, because they are unprompted.

| Area | Prompt | Candidates found |
|---|---|---|
| **Repetition** | What do you do more than twice a week, the same way each time? | |
| **Copying** | Where does data get retyped from one system into another? | |
| **Waiting** | What sits in a queue because one person has to touch it? | |
| **Chasing** | What do you have to remind people about? | |
| **Assembly** | What report or pack gets rebuilt from the same sources each time? | |
| **After hours** | What gets done outside working hours because it cannot wait? | |
| **Errors** | What gets redone because it was wrong the first time? | |
| **Key person** | What stops entirely when one specific person is away? | |

> **The last row is the one people skip and then regret.** A task only one person can do
> is a business continuity risk before it is an automation opportunity, and it is usually
> undocumented — which means it must be written down (02) before anything else happens
> to it.

---

## Score each candidate

One block per candidate. Keep it to the numbers the owner actually knows — a guess you
can defend beats a precise number you invented.

```
CANDIDATE:                ____________________________________
Who does it today:        ____________________________________
Who owns the outcome:     ____________________________________

FREQUENCY
  Times per month:        ______
  Minutes each time:      ______
  People involved:        ______
  Loaded hourly cost:     $______   (salary + overhead, not salary alone)

QUALITY
  Redone due to error:    ______%  of runs
  What a mistake costs:   [ ] Annoying  [ ] Expensive  [ ] Customer-visible  [ ] Regulatory

DEPENDENCIES
  Systems it touches:     ____________________________________
  Do we control them:     [ ] All  [ ] Some  [ ] None
  Has an API / export:    [ ] Yes  [ ] Partly  [ ] No — manual only

DOCUMENTATION
  Written down anywhere:  [ ] Fully  [ ] Partly  [ ] Only in someone's head

CHANGE
  Changed in last 6 mths: [ ] No  [ ] Minor  [ ] Substantially
  Expected to change:     [ ] No  [ ] Possibly  [ ] Yes — known change coming

DESIRED OUTCOME (pick one, be specific)
  [ ] Less time spent      [ ] Fewer errors        [ ] Faster turnaround
  [ ] Less after-hours     [ ] Reduced key-person risk
  [ ] Better records       [ ] Other: ______________________

  How we would know it worked: _______________________________
```

---

## Disqualify early

Rule a candidate out now — cheaply — if any of these hold:

| Signal | Why it disqualifies |
|---|---|
| **Undocumented and only in one head** | You would be automating a guess. Document it first (02), then reassess. |
| **The process changes substantially every quarter** | The automation becomes maintenance you did not budget for. |
| **No API, no export, no structured input** | Screen-scraping a UI you do not control breaks on someone else's release schedule. |
| **The real problem is a decision, not a task** | Automation makes a bad decision faster. Fix the decision. |
| **Nobody owns the outcome** | Nothing to hand the automation to, and nobody to notice when it fails. |
| **It runs fewer than a few times a month and takes minutes** | The implementation will never pay back. Check with 09 if unsure. |

Write down *why* something was ruled out. Six months later that note stops the same
candidate being re-proposed from scratch.

---

## Output of this step

A shortlist, each entry carrying: the numbers, an owner, a named desired outcome, and a
way to tell whether it worked.

Take that shortlist to **02** to document how the work is really done, then **03** to
rank it. Do not skip to picking a tool — the tool is the last decision, not the first.

---

*© ClearGlass Inc. Original work. Planning aid only; no guarantee of savings,
compliance, performance or business outcomes.*
