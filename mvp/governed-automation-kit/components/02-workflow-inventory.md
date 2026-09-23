# 02 — Workflow Inventory Template

> Documents how the work is *actually* done, before anyone changes it.
> Feeds **03** (ranking) and **04** (risk scoring).
>
> A planning aid. Not legal, tax, financial, compliance or security advice.

---

## The rule

**Document the process that happens, not the one on the org chart.** The gap between them
is where automation projects die — you build for the documented path and discover the
real one has three exceptions, a spreadsheet nobody mentioned, and a step that exists
because of something a customer did in 2023.

Write it by watching it once, or by sitting with the person who does it. Not from memory.

---

## One record per workflow

```
WORKFLOW:                 ____________________________________
ID:                       WF-____
Owner (accountable):      ____________________________________
Performed by:             ____________________________________
Backup performer:         ____________________ (blank = key-person risk)
Frequency:                ______ / month
Typical duration:         ______ minutes

TRIGGER — what starts it
  [ ] Schedule: ____________  [ ] Event: ____________
  [ ] Request from: ________  [ ] Someone notices: ____________

INPUTS
  Source                        Format          Do we control it?
  ____________________          ____________    [ ] Y [ ] N
  ____________________          ____________    [ ] Y [ ] N

STEPS — as actually performed
  #   Action                          System        Manual?   Decision?
  1   ____________________________    __________    [ ]       [ ]
  2   ____________________________    __________    [ ]       [ ]
  3   ____________________________    __________    [ ]       [ ]
  4   ____________________________    __________    [ ]       [ ]

  Mark "Decision?" where a person exercises judgement.
  Those steps are your gate candidates in 04 — and the ones automation
  is least able to take over.

OUTPUTS
  What is produced:       ____________________________________
  Who receives it:        ____________________________________
  Where it is stored:     ____________________________________

HANDOFFS — where it leaves one person's hands
  From ____________ to ____________ via ____________
  From ____________ to ____________ via ____________

EXCEPTIONS — the part everyone forgets
  What goes wrong:        ____________________________________
  How often:              ______% of runs
  Who handles it:         ____________________________________
  Is the fix documented:  [ ] Yes  [ ] No

DATA SENSITIVITY
  [ ] Public   [ ] Internal   [ ] Confidential   [ ] Personal data
  [ ] Payment / financial     [ ] Health         [ ] Other regulated: ________
  → Anything below "Internal" raises the risk score in 04.

DOCUMENTATION STATE
  [ ] Written and current   [ ] Written but stale   [ ] Partly   [ ] Not written
```

---

## The exception rate is the finding

If exceptions run above roughly **one in five**, you are not looking at a process with
some edge cases. You are looking at **two or more processes** wearing one name.

Split them and inventory each separately. Automating the blended version produces
something that handles neither well and needs a human for both.

---

## Inventory summary

| ID | Workflow | Owner | Runs/mo | Min/run | Manual steps | Decisions | Exceptions | Data | Documented |
|----|----------|-------|---------|---------|--------------|-----------|-----------|------|------------|
| WF-01 | | | | | | | % | | |
| WF-02 | | | | | | | % | | |
| WF-03 | | | | | | | % | | |

Read the finished table across, not down. Three patterns matter:

- **Many manual steps, few decisions** → strong automation candidate.
- **Few manual steps, many decisions** → a documentation and training problem, not an
  automation one. Automating it will produce a fast wrong answer.
- **No backup performer** → fix the continuity risk first. It is cheaper and more urgent
  than any automation on the list.

---

*© ClearGlass Inc. Original work. Planning aid only.*
