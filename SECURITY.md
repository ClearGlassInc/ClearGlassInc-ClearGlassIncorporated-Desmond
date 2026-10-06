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
How the repository's GitHub Actions are kept from becoming the attack path. Details and settings: `AUTOMATION.md`.

### Credentials
- Deploy credentials are GitHub **environment** secrets (`staging`, `production`), readable only by jobs bound to that environment, so staging and production never share one.
- The Render deploy hook (`RENDER_DEPLOY_HOOK`) is a long-lived URL credential. Rotate it in Render if it is ever exposed.
- No cloud provider is wired yet. When one is, it authenticates with OIDC, never a stored key, and its trust policy names the environment (`repo:ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond:environment:production`), not the whole repository.
- Secrets reach scripts through `env:`, never by `${{ }}` interpolation into a script. `scripts/audit_github_actions.py` fails any workflow that does otherwise.

### Supply chain
- Every external action is pinned to a full commit SHA (`scripts/workflow_doctor.py` fails on a tag or branch).
- Every workflow declares least-privilege `permissions`; write scopes sit on the job that needs them.
- `CODEOWNERS` requires owner review for `.github/workflows/` and `.github/actions/`.

### Fork and pull-request safety for auto-fix
- Auto-fix runs only for pull requests from this repository, never forks, and never for bot authors or PRs labelled `no-autofix`.
- Pull-request code runs only in a read-only job. The job holding the write token runs none of it: it applies the resulting patch, refuses any path `scripts/automation_governance.py` protects or anything under `.github/`, and pushes without force.
- At most two `auto-fix:` commits per pull request, which prevents fix loops.
- Deploy and comment jobs load shared actions from the default branch, so a pull request cannot alter code that runs beside an environment's secrets.
