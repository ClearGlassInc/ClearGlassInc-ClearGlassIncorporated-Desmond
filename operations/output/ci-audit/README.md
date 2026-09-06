# ClearGlassInc CI Audit — honest report

Run date: 2026-06-26. Org has **5 repositories** (not 1000).

This report records only what was actually checked. Findings are labelled by
whether they were **independently verified in this session** or carried over
from a prior run that had wider repository access.

## Summary

| Repo | Finding | Verified this session |
|------|---------|-----------------------|
| `ClearGlassInc.github.io` | "Running Copilot cloud agent" fails hourly at **Processing Request (Linux)** | ✅ yes |
| `Gaurdian` | Cert Bot fails at **Check certificate expirations** | ❌ no (out of scope) |
| `Opal-Koboi` | Pages deploy fails at **Setup Pages**; Copilot Setup Steps fails (main CI green) | ❌ no (out of scope) |
| `safe-add-animations.ps1` | Dependabot/code-scanning alerts **disabled** | ⚠️ partial |
| `Opal-Koboi` | Dependabot/code-scanning alerts **disabled** | ⚠️ partial |

## Detail

### 1. ClearGlassInc.github.io — Copilot cloud agent failing hourly (VERIFIED)

The **"Running Copilot cloud agent"** runs are failing every hour
(09:08, 10:08, 11:08, 12:08, 13:08 UTC — all `failure`). The failing step is
**#14 "Processing Request (Linux)"**, failing ~4s into the job.

This is **not a workflow file in this repository.** It is GitHub's managed
`dynamic/copilot-swe-agent/copilot` workflow, driven by an assigned Copilot
coding-agent task (head branch `copilot/task-272290681-1196426665-...`). There
is **no in-repo code edit that fixes it.** All other workflows in this repo are
green.

**Remediation (GitHub-side, not a code change):** cancel/unassign the stuck
Copilot coding-agent task, or resolve the underlying Copilot quota/access error
that surfaces as "Processing Request" failing. Until then it will keep
re-firing and failing hourly.

### 2. Gaurdian — Cert Bot (REPORTED, not verified this session)

Prior run reported the **Cert Bot** failing at **Check certificate
expirations**. This session's GitHub access is scoped to
`www.clearglassinc.com` only; `Gaurdian` returns *access denied* and the
`list_repos`/`add_repo` tooling was not available, so this could **not be
independently re-verified.** Treat as carried-over, not confirmed.

### 3. Opal-Koboi — Pages + Copilot Setup (REPORTED, not verified this session)

Prior run reported **Pages deploy** failing at **Setup Pages** and **Copilot
Setup Steps** failing, with main CI green. Out of scope this session — not
re-verified. ("Setup Pages" typically fails when Pages is not enabled / has no
configured source in repo settings — worth checking first.)

### 4. Security posture — "0 vulnerabilities" is UNVERIFIED

The clean-security claim is **not substantiated**:

- The token used cannot read Dependabot / code-scanning alerts.
- Alerts are **disabled** on `safe-add-animations.ps1` and `Opal-Koboi`, so
  there is nothing to read even with permission.

Enable Dependabot + code scanning on all repos and grant alert-read scope
before asserting a clean posture, then re-audit.

## Why the auto-patch/push phase was NOT run

The audit's auto-patch phase was **intentionally withheld** — it is unsafe to
run unattended:

1. It **blind-commits unreviewed edits to every repo**, with no review/dry-run
   gate.
2. Its `sed` commands are **broken**: `sed -i` is pointed at a directory, which
   errors out.

Do not run it as-is. Fix the `sed` target and add a dry-run + human-review gate
before any automated cross-repo commits.

---

Machine-readable version: [`github_audit_report.csv`](./github_audit_report.csv)
