# CI automation and PR staging repair

## What this change adds

- `.github/workflows/pr-staging.yml` runs for PRs targeting `main` or `staging`.
- Every run uses a fresh GitHub-hosted runner, read-only repository permissions, pinned Actions, a per-PR concurrency group, and a bounded execution time.
- Where a root `package-lock.json` exists, the workflow performs a locked install, type-check, tests, build verification, and a localhost smoke test of the built application.
- A run-scoped evidence artifact records the source SHA and run URL. No PR code receives write credentials, cloud secrets, or production credentials.

## Important deployment boundary

This is an isolated, ephemeral **CI staging preview**, not a public cloud deployment. The repository's existing `scripts/ci/deploy-staging.sh` still contains a `REPLACE_ME_DEPLOY_COMMAND` placeholder. Existing baseline and remediation documentation also identify staging-provider configuration and GitHub Actions entitlement/settings as external prerequisites.

Do not represent this runner preview as a deployed Cloud Run, ECS, Kubernetes, or Render environment. A real per-PR cloud deployment requires an owner-selected provider, OIDC trust configuration, a staging project/account, and a configured deploy/cleanup adapter. None is inferred or fabricated here.

## automation-write environment

The existing `automation-write` environment is intentionally retained as an approval boundary for repository-mutating automation. Do not remove the environment or bypass required reviewers to make a red deployment indicator disappear. A repository administrator must verify that the environment exists, has the intended required reviewers, restricts deployment branches, and has only environment-scoped secrets.

The existing Auto Heal workflow currently subscribes to all workflow completions and scans unrelated scheduled failures. Its repeated failures should be diagnosed from the actual job logs and environment configuration before changing its write authority. The GitHub API returned no job steps for the sampled failed run, so source inspection alone cannot establish the remote failure cause.

## Verification

1. Open a PR targeting `main` or `staging`.
2. Confirm the `PR Staging / staging` check runs and inspect the uploaded evidence artifact.
3. Confirm the PR check does not have write permissions or cloud credentials.
4. Configure the cloud staging adapter and OIDC trust separately before claiming a cloud deployment.
5. Test `automation-write` with a no-change run after an administrator confirms environment protection and Actions entitlement.
6. Keep GitHub Pages and production promotion workflows unchanged.
