# ClearGlass Inc. Security Policy

## Scope
This policy applies to the public ClearGlassInc Artemis GitHub Pages and supporting documentation repository.

## Supported versions
| Branch / Version | Supported |
| --- | --- |
| `main` (current production content) | ✅ |
| Legacy snapshots and archived exports | ⚠️ Best effort |

## Reporting a vulnerability
Report vulnerabilities privately by opening a GitHub private vulnerability report:

https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/security/advisories/new

If GitHub private vulnerability reporting is unavailable, email the security owner at
`desmondotieno@icloud.com` with the subject prefix `[SECURITY] ClearGlassInc Artemis`.
Do not open a public issue for suspected vulnerabilities, secrets, authentication bypasses,
or exploit details.

Please include:
- impacted file, endpoint, or feature;
- reproducible steps;
- potential impact and exploit conditions;
- proof-of-concept (if safe and lawful).

## Response timeline
- **Acknowledgment:** within 1 business day
- **Initial triage:** within 3 business days
- **Status updates:** at least every 5 business days until closure

## Safe harbor expectations
Good faith security research is permitted when it:
- avoids service disruption;
- avoids unauthorized data access, exfiltration, or persistence;
- remains within legal and ethical boundaries;
- is reported promptly and confidentially.

## Disclosure process
- Coordinated disclosure is preferred.
- Public disclosure should follow remediation or mutual agreement.
- Severity scoring and remediation decisions are handled by the ClearGlassInc Artemis security owner.

## Security commitments
ClearGlassInc Artemis follows secure by design principles including least privilege, access control, logging, and policy-driven change management.

## CI/CD security
The automation layer is described in `AUTOMATION.md`. These controls apply to it and to
every other workflow in `.github/workflows/`.

### Workflow supply chain
- Every external action is pinned to a full 40-character commit SHA, with the version in a
  trailing comment. `scripts/workflow_doctor.py` and `scripts/audit_github_actions.py` fail
  CI on an unpinned action, including inside local composite actions.
- Workflows declare an explicit top-level `permissions:` block (normally `contents: read`)
  and grant write scopes only to the job that uses them.
- Secrets reach scripts through `env:`, never through `${{ secrets.* }}` interpolated into a
  `run:` block (the audit fails CI on it). Untrusted event text (PR titles and bodies,
  branch names, comments) must be passed the same way, never interpolated into shell or
  `github-script` source.
- `pull_request_target` is prohibited without a documented trust-boundary review.
- `.github/workflows/` and `.github/actions/` are owned in `CODEOWNERS`. Branch protection
  on `main` must require code-owner review for that ownership to block a merge.

### Environment secrets
- Deployment credentials must be environment secrets on `staging` and `production`, never
  repository secrets shared between them. The `production` environment must require
  reviewers and accept deployments from `main` only. Both are repository settings; this
  file cannot enforce them.
- A deploy names a full commit SHA, never a branch or tag that can move between approval
  and deployment.
- Secret values are never echoed. Deploy hook URLs carry a key and are treated as secrets.

### Cloud credentials (OIDC)
When a deployment moves to a cloud provider, credentials come from GitHub's OIDC token,
not long-lived keys. Bind each role to one environment through the `sub` claim, so a
workflow on a feature branch cannot assume the production role:

```json
{
  "Effect": "Allow",
  "Principal": {
    "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:environment:production"
    }
  }
}
```

A wildcard subject such as `repo:OWNER/REPO:*` lets any branch, PR or workflow in the
repository assume the role. Do not use one. GCP Workload Identity Federation and Azure
federated credentials take the same environment-scoped subject.

### Fork and PR safety for auto-fix
- Auto-fix runs only for pull requests whose head is in this repository, never forks.
- It skips bot-authored PRs, PRs labelled `no-autofix`, and branches that moved after
  the failing run, and stops after 2 auto-fix commits on one PR.
- It runs only `ruff check --fix` (safe fixes). Nothing from the PR is executed, and no
  dependency from the PR is installed, while the job holds a write token.
