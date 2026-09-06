# SOC Purple-Team Exercise Plan & Detection-Engineering Playbook

> Companion document to the executable `sentinel/sentinel/purpleteam.py`
> engine. Defensive only — runs against the operator's **owned, authorized**
> environment. Every engagement carries a documented `authorization_ref` and
> explicit `scope`; the engine fails closed otherwise.

---

## 1. Purpose

Purple teaming is the collaborative cycle in which the offensive (red) and
defensive (blue) functions work side-by-side to **measure, tune, and verify**
detection and response. The output is not a "win" but **measurable improvement**
— detection rate up, MTTD down, fewer open gaps, broader ATT&CK coverage.

## 2. Operating principles

- **Defensive only.** SENTINEL executes no offensive code. Adversary techniques
  are introduced by an authorized red engagement (internal or vendor); SENTINEL
  records outcomes and drives the tuning loop.
- **Authorized scope is mandatory.** Engagement creation requires a written
  authorization reference and an explicit list of owned systems in scope.
- **Fail-closed.** Missing authorization / scope → `PurpleTeamError` and the
  cycle does not start.
- **Audited.** Every step (`scope`, `simulate`, `tune`, `retest`, `report`)
  appends to the hash-chained audit log; `report.audit_ref` is the evidence
  pointer.

## 3. The cycle

```
   1 SCOPE        objective, technique, log sources, success metric
       │
   2 SIMULATE     red executes the technique within scope
       │
   3 OBSERVE      blue records outcome: DETECTED / PARTIAL / MISSED, TTD
       │
   4 SCORE        detection rate, MTTD, per-tactic coverage, open gaps
       │
   5 TUNE         detection-engineering: rule / threshold / log source
       │
   6 RETEST       re-simulate and capture improved outcome / TTD
       │
   7 VERIFY       if the result improved, the gap closes; else iterate
       │
   8 REPORT       evidence-based summary + audit_ref for the engagement
```

## 4. Scenario template (executable shape)

Each scenario is a single, **scoped objective** with a measurable success
condition and the telemetry expected to catch it.

```python
Scenario(
  objective="Detect malicious PowerShell on owned endpoints",
  technique=Technique("T1059.001", "PowerShell", Tactic.EXECUTION),
  log_sources=("EDR", "script-block-logs"),
  success_metric="alert within 10m",
)
```

## 5. Detection-engineering playbook

For each scenario the blue team produces an evidence-backed change to the
detection stack. The minimum acceptable record is:

| Field | Example |
|---|---|
| Hypothesis | "child process of Office app → suspicious PS" |
| Data source | EDR process-tree + script-block-logs |
| Rule (Sigma-style) | `image: powershell.exe AND parent_image in (winword.exe, excel.exe)` |
| Severity | medium |
| Owner | SOC L2 |
| FP control | exclude signed enterprise scripts |
| Verification | retest improves outcome to DETECTED, TTD < 10m |
| Rollback | revert rule id `R-PS-031` |

The engine's `tune(step, "rule-id-or-description")` records the pointer; the
retest proves the change worked, and `report()` exposes the deltas.

### Default detections to ship in Phase One

| Tactic | Technique | Telemetry | First rule shape |
|---|---|---|---|
| Execution | T1059.001 PowerShell | EDR + script-block | suspicious child + base64 hints |
| Cred Access | T1003 OS Cred Dump | EDR | LSASS handle access by non-system process |
| Persistence | T1547.001 Run keys | EDR + registry audit | non-baseline writes to `Run\*` |
| Defense Evasion | T1218 LOLBins | EDR + proxy | rundll32/mshta with remote URL |
| Lateral | T1021.002 SMB Admin Shares | auth + EDR | non-admin → ADMIN$/C$ |
| Exfil | T1041 C2 over web | proxy + EDR | beaconing + uncommon ASNs |

## 6. Scoring rubric (mirrors the engine)

- `detection_rate` = `DETECTED` / scenarios (initial)
- `post_tune_rate` = `DETECTED` after retest / scenarios
- `mttd_min` = mean time-to-detect across all scenarios that produced a TTD
- `coverage[tactic]` = `DETECTED` fraction per ATT&CK tactic
- `open_gaps` = remaining un-DETECTED scenarios with rationale

A green engagement = `post_tune_rate ≥ 0.9`, `mttd_min ≤ scenario metric`, and
**zero** open gaps that touch critical-system tactics (Cred Access, Exfil,
Persistence on tier-0).

## 7. Roles & operating cadence

| Role | Responsibility |
|---|---|
| Engagement owner | scope, authorization, sign-off |
| Red lead | technique selection within scope, safe execution |
| Blue lead | telemetry readiness, scoring, tuning |
| Detection engineer | rule design, FP control, rollback |
| Reviewer | reads `report()` + audit chain before close |

**Cadence:** weekly small-batch (3 scenarios), monthly themed (one tactic deep
dive), quarterly full-board.

## 8. Sample engagement (drives the engine)

```python
from sentinel.purpleteam import (
  Engagement, PurpleTeamEngine, Scenario, Technique, Tactic, Outcome,
)

eng = Engagement(
  name="Q3-owned-corp",
  authorization_ref="PT-AUTH-2026-09",
  scope="owned corp endpoints + cloud tenancy",
  jurisdiction="US-CA",
)
pt = PurpleTeamEngine(eng)

s = pt.simulate(
  Scenario("Detect LSASS access", Technique("T1003","Cred Dump",Tactic.CRED_ACCESS),
           ("EDR",), "alert within 15m"),
  outcome=Outcome.MISSED,
)
pt.tune(s, "Sigma: LSASS handle access by non-system process")
pt.retest(s, outcome=Outcome.DETECTED, ttd_min=8)

print(pt.report().top_line)
# e.g. "100% detection after tuning (+100 pts), MTTD 8.0m, 0 open gap(s)."
```

## 9. Closure & evidence pack

A passing engagement produces:
- `report.top_line`, `detection_rate`, `post_tune_rate`, `mttd_min`,
  `coverage`, `open_gaps`
- the engine's `AuditLog` (hash-chained), exportable for compliance
- the rule/playbook diffs landed in the detection stack
- the change tickets opened for any deferred open gap
