# Azure OIDC production deployment — activation runbook

Turns a GitHub Actions → Azure Functions deployment from a long-lived
`AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret into short-lived federated (OIDC)
credentials that only mint a token for a **protected** environment.

Driver: [`scripts/azure_oidc_activation.sh`](../scripts/azure_oidc_activation.sh).
Nothing mutates without `--apply`; the default run prints the exact API calls and
the current state of every item.

## Why the order matters

The three controls only add up to something when they are applied together:

- The **federated credential** replaces a reusable secret with a token minted
  per run.
- Pinning the **subject** to `repo:<owner>/<repo>:environment:production` means
  a run that is not deploying to that environment cannot get a token at all —
  a fork PR or a scratch branch gets nothing.
- **Required reviewers** on the environment are what make that subject a real
  gate. Without them the environment is a label, and the subject restriction
  buys nothing.

Publish-profile deletion comes **last**, and only after a green OIDC run. Delete
it earlier and the only working deployment credential is gone.

## Prerequisites

| Credential | Needed for | Notes |
|---|---|---|
| `GITHUB_TOKEN` | steps 1–5, 8, 9, 10 | Fine-grained PAT: Variables (write), Secrets (write), Environments (write), Actions (write), Administration (read). The Actions-provided `GITHUB_TOKEN` **cannot** do this. |
| `az login` session | steps 6, 7 | Needs Application Administrator (or ownership of the app registration) and rights to assign a role on the function app. |

The script reads the token from the `GITHUB_TOKEN` environment variable only —
same auth model as `scripts/repo_audit.sh` and `scripts/fix_pages_source.sh`. It
never calls `gh auth login` and never reads a token from disk.

## Run it

```bash
export GITHUB_TOKEN=github_pat_xxx

export AZURE_CLIENT_ID=<app registration client id>
export AZURE_TENANT_ID=<directory tenant id>
export AZURE_SUBSCRIPTION_ID=<subscription id>
export AZURE_FUNCTIONAPP_NAME=<function app name>
export AZURE_RESOURCE_GROUP=<resource group>        # for the role assignment
export REQUIRED_REVIEWERS='user:dezzy231'           # or 'team:platform', comma-separated

az login

# 1. review — read-only, changes nothing
scripts/azure_oidc_activation.sh --repo ClearGlasslabs/Opal-Koboi

# 2. apply everything except the run and the cleanup
scripts/azure_oidc_activation.sh --repo ClearGlasslabs/Opal-Koboi --apply --step variables
scripts/azure_oidc_activation.sh --repo ClearGlasslabs/Opal-Koboi --apply --step federation
scripts/azure_oidc_activation.sh --repo ClearGlasslabs/Opal-Koboi --apply --step environment

# 3. prove it works — the run pauses for reviewer approval before deploying
scripts/azure_oidc_activation.sh --repo ClearGlasslabs/Opal-Koboi --apply --step verify

# 4. only once that run is green
scripts/azure_oidc_activation.sh --repo ClearGlasslabs/Opal-Koboi --apply --step cleanup
```

Every phase is idempotent — re-running reports `ok` for what is already in place.

## Checklist coverage

| # | Checklist item | Phase | How it is satisfied |
|---|---|---|---|
| 1 | Add repository variable `AZURE_CLIENT_ID` | `variables` | `POST`/`PATCH /repos/{repo}/actions/variables` |
| 2 | Add repository variable `AZURE_TENANT_ID` | `variables` | same |
| 3 | Add repository variable `AZURE_SUBSCRIPTION_ID` | `variables` | same |
| 4 | Add repository variable `AZURE_FUNCTIONAPP_NAME` | `variables` | same |
| 5 | Confirm `AZURE_FUNCTIONAPP_PACKAGE_PATH` if the package is not `api` | `variables` | Reads the workflow, prints its default, and writes the variable only when it differs |
| 6 | Create an Entra federated identity credential | `federation` | `az ad app federated-credential create`, issuer `https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange` |
| 7 | Restrict the federated subject to `production` | `federation` | Subject is `repo:<owner>/<repo>:environment:production` — nothing broader is ever created |
| 8 | Protect the GitHub `production` environment with required reviewers | `environment` | `PUT /repos/{repo}/environments/production`; resolves user logins and team slugs to IDs, and fails if none resolve rather than writing an empty gate |
| 9 | Run the workflow manually and verify OIDC + deployment | `verify` | `workflow_dispatch`, plus a static check that the workflow declares `id-token: write`, uses `azure/login`, and names an `environment` |
| 10 | Delete or rotate `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | `cleanup` | Refuses to delete unless a **successful** run of the workflow already exists |

## The step the checklist does not name

A federated credential proves *identity*; it grants no *permissions*. Without a
role on the function app, `azure/login` succeeds and the deploy step then fails
with an authorization error. The `federation` phase therefore also assigns
`$AZURE_ROLE` (default `Contributor`) at the function app's scope when
`AZURE_RESOURCE_GROUP`, `AZURE_FUNCTIONAPP_NAME` and `AZURE_SUBSCRIPTION_ID` are
all set. Narrow it with `AZURE_ROLE=Website Contributor` if that is sufficient
for the deployment method in use.

## Options

| Flag / variable | Default | Meaning |
|---|---|---|
| `--repo owner/repo` | *(required)* | Target repository |
| `--apply` | off | Perform writes; otherwise dry run |
| `--step <name>` | `all` | One of `variables`, `federation`, `environment`, `verify`, `cleanup` |
| `--environment` / `ENVIRONMENT` | `production` | Environment name, also used in the federated subject |
| `--workflow` / `AZURE_WORKFLOW_FILE` | `azure-functions.yml` | Workflow file name |
| `--ref` / `AZURE_WORKFLOW_REF` | `main` | Ref to dispatch |
| `AZURE_FUNCTIONAPP_PACKAGE_PATH` | `api` | Deployable package path |
| `AZURE_ROLE` | `Contributor` | Role assigned at the function app scope |
| `FEDERATED_CREDENTIAL_NAME` | `github-<repo>-<environment>` | Credential name |

## Troubleshooting

**`AADSTS70021: No matching federated identity record found`** — the subject in
the token does not match the credential. The run must target the environment
named in the subject; a job without `environment: production` produces
`repo:owner/repo:ref:refs/heads/main` instead, which is exactly the case this
setup is meant to reject.

**`workflow_dispatch failed (HTTP 422)`** — the workflow has no
`workflow_dispatch:` trigger on the dispatched ref.

**Deploy fails after a successful `azure/login`** — identity without
authorization; see the role assignment section above.

**The run sits in "Waiting"** — that is the required-reviewer gate doing its job.
Approve it in the Actions UI.
