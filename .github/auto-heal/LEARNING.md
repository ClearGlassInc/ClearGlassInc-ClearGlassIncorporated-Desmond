# Auto-Heal Learning Log

Written by people and agents, not by `auto_heal.py`. Each entry records a
failure pattern, what fixed it or worked around it, and whether that held. The
four learning loops in `prompts/repair/debug-deploy-master-prompt.md` write
here.

Rules:

- Append only. When an entry turns out to be wrong, add a new entry that
  corrects it; do not rewrite the old one.
- Every entry names its evidence: a run URL, job ID, commit SHA, PR link or
  command output. Without one, the result is `NOT VERIFIED`.
- A workaround is tagged `temporary` and carries an expiry date and the
  condition that removes it.
- Numbers only when measured.

Entry format:

```
## YYYY-MM-DD: <short title>
- Tags: <category>[, temporary]
- Evidence: <run URL | job ID | commit | PR | command + output>
- Problem: <what failed, exact error text where there is one>
- Fix or workaround: <what was done, with the commit>
- Result: <measured outcome, or NOT VERIFIED>
- Remove when: <temporary entries only, plus an expiry date>
- Applies to: <other workflows or paths with the same exposure>
```

---

## 2026-09-29: Actions jobs get no runner

- Tags: runner-entitlement, temporary
- Evidence: job `109519331157` (ClearGlass GitHub Pages Check, `main` at
  `1d3c2a0`, 2026-09-29) reported `runner_id: 0`, empty `runner_name`, 4
  seconds. Earlier jobs with the same result: `104850767490` (2026-09-16),
  `107260634855` (2026-09-23), `107658897347` (2026-09-24), all recorded in
  `CLAUDE.md`.
- Problem: since 2026-09-06 user-authored jobs are never given a runner. They
  fail within seconds with no steps and no logs. GitHub-managed jobs (Pages
  build and deployment, Dependabot) still run.
- Fix or workaround: none is possible in the repository; it is an
  organisation setting (billing hold, spending limit, allowed-actions policy or
  the Actions toggle). Workaround: run `python3 scripts/ci_local.py` locally
  and use its output as the evidence.
- Result: open.
- Remove when: a job on `main` reports a non-zero `runner_id`. Re-check on
  every session; no fixed expiry, because a human has to change the setting.
- Applies to: all 84 workflows, including `auto-heal.yml` itself. Auto-heal
  cannot detect or heal this class of failure: its job gets no runner either,
  and there is no log text for `error-patterns.json` to match.

## 2026-09-29: Completion reported for a branch that was never pushed

- Tags: evidence
- Evidence: `git fetch origin codex/merge-role-devops-reliability` returned
  `fatal: couldn't find remote ref`; `git ls-remote --heads origin` listed 89
  branches, none under `codex/`; no pull request had that head. The same
  branch name was also absent from `ClearGlasslabs/ClearGlassInc.`.
- Problem: an agent's handoff said a "Merge Role" mandate had been added on
  `codex/merge-role-devops-reliability` and was ready for review. The branch
  did not exist on GitHub.
- Fix or workaround: accept a completion claim only with a ref that resolves.
  `git ls-remote --heads origin <branch>` has to print a SHA, or the claim has
  to link a pull request.
- Result: applied from this entry on.
- Applies to: every agent handoff, whichever tool produced it.

## 2026-09-29: Generic CI workarounds fail this repository's own gates

- Tags: config, security
- Evidence: a scratch workflow built from a pasted draft of the master prompt,
  run through `scripts/audit_github_actions.py` and
  `scripts/workflow_doctor.py`, gave 3 ERRORs (`actions/checkout@v4` and
  `nick-fields/retry@v2` not pinned to a SHA; a secret interpolated into a
  `run:` script) and a warning for `continue-on-error` on an install step. The
  replacement example in `prompts/repair/debug-deploy-master-prompt.md` came
  back `valid and ready` with 0 errors from both.
- Problem: the usual advice (tag pins, a secret checked inside `run:`,
  `continue-on-error` around a flaky step, `exit 0` when a secret is missing)
  either breaks the gates here or hides a failure behind a green check.
- Fix or workaround: pass secrets through `env` and gate on their presence so
  the skip is visible; retry in shell instead of adding a third-party action;
  pin everything to a SHA; no `continue-on-error` on a critical step.
- Result: verified against both gates, on the command output above.
- Applies to: any workflow change made from a generic DevOps prompt or
  template.
