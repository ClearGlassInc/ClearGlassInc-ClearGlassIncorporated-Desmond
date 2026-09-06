#!/usr/bin/env bash
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#
# Azure OIDC production deployment activation.
#
# Executes the cloud-side activation checklist that turns a GitHub Actions ->
# Azure Functions deployment from a long-lived publish profile into short-lived
# federated (OIDC) credentials scoped to a protected environment:
#
#   1-4  repository variables AZURE_CLIENT_ID / AZURE_TENANT_ID /
#        AZURE_SUBSCRIPTION_ID / AZURE_FUNCTIONAPP_NAME
#   5    AZURE_FUNCTIONAPP_PACKAGE_PATH, confirmed against the workflow
#   6-7  Microsoft Entra federated identity credential, subject restricted to
#        repo:<owner>/<repo>:environment:<environment>
#   8    GitHub environment protected with required reviewers
#   9    manual workflow run + OIDC/deployment verification
#   10   AZURE_FUNCTIONAPP_PUBLISH_PROFILE deleted once OIDC is proven
#
# Auth model (same as scripts/repo_audit.sh and scripts/fix_pages_source.sh):
# the GitHub token is read from the GITHUB_TOKEN environment variable only.
# It needs a fine-grained PAT with repo permissions Variables (write), Secrets
# (write), Environments (write), Administration (read) and Actions (write) --
# the default Actions GITHUB_TOKEN cannot write variables or environments.
# Azure calls go through an already-authenticated `az` CLI (`az login`), whose
# identity needs Application Administrator (or ownership of the app
# registration) plus rights to assign a role on the function app.
#
# Nothing mutates without --apply. The default run is a dry run that prints the
# exact API calls and reports current state, so the checklist can be reviewed
# before anything is touched.
#
#     export GITHUB_TOKEN=github_pat_xxx
#     export AZURE_CLIENT_ID=... AZURE_TENANT_ID=... AZURE_SUBSCRIPTION_ID=...
#     export AZURE_FUNCTIONAPP_NAME=... AZURE_RESOURCE_GROUP=...
#     scripts/azure_oidc_activation.sh --repo ClearGlasslabs/Opal-Koboi
#     scripts/azure_oidc_activation.sh --repo ClearGlasslabs/Opal-Koboi --apply
#
# Individual phases can be run on their own, e.g. only the final cleanup:
#     scripts/azure_oidc_activation.sh --repo owner/repo --step cleanup --apply
#
set -euo pipefail

REPO=""
ENVIRONMENT="${ENVIRONMENT:-production}"
WORKFLOW_FILE="${AZURE_WORKFLOW_FILE:-azure-functions.yml}"
WORKFLOW_REF="${AZURE_WORKFLOW_REF:-main}"
PACKAGE_PATH="${AZURE_FUNCTIONAPP_PACKAGE_PATH:-api}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-}"
REQUIRED_REVIEWERS="${REQUIRED_REVIEWERS:-}"
ROLE="${AZURE_ROLE:-Contributor}"
APPLY=0
STEP="all"

API="https://api.github.com"
FEDERATED_ISSUER="https://token.actions.githubusercontent.com"
FEDERATED_AUDIENCE="api://AzureADTokenExchange"
PUBLISH_PROFILE_SECRET="AZURE_FUNCTIONAPP_PUBLISH_PROFILE"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)        REPO="$2"; shift 2 ;;
    --environment) ENVIRONMENT="$2"; shift 2 ;;
    --workflow)    WORKFLOW_FILE="$2"; shift 2 ;;
    --ref)         WORKFLOW_REF="$2"; shift 2 ;;
    --step)        STEP="$2"; shift 2 ;;
    --apply)       APPLY=1; shift ;;
    -h|--help)     sed -n '3,45p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$REPO" ]] || { echo "error: --repo owner/repo is required" >&2; exit 2; }
OWNER="${REPO%%/*}"
NAME="${REPO##*/}"
SUBJECT="repo:${OWNER}/${NAME}:environment:${ENVIRONMENT}"

step_wanted() { [[ "$STEP" == "all" || "$STEP" == "$1" ]]; }
say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32mok\033[0m    %s\n' "$*"; }
warn() { printf '   \033[33mwarn\033[0m  %s\n' "$*"; }
skip() { printf '   \033[90mdry\033[0m   %s\n' "$*"; }
die()  { printf '   \033[31mfail\033[0m  %s\n' "$*" >&2; exit 1; }

# GitHub REST helper: gh_api METHOD PATH [json-body]. Deliberately returns its
# result through the globals GH_BODY / GH_STATUS rather than stdout -- capturing
# stdout with $(...) would run it in a subshell, where the GH_STATUS assignment
# is discarded and callers silently branch on the *previous* call's status.
GH_BODY=""
GH_STATUS=""
gh_api() {
  local method="$1" path="$2" body="${3:-}" out
  local -a args=(-sS -X "$method" -w '\n%{http_code}'
    -H "Authorization: Bearer ${GITHUB_TOKEN}"
    -H "Accept: application/vnd.github+json"
    -H "X-GitHub-Api-Version: 2022-11-28")
  [[ -n "$body" ]] && args+=(-H "Content-Type: application/json" -d "$body")
  out="$(curl "${args[@]}" "${API}${path}")"
  GH_STATUS="${out##*$'\n'}"
  GH_BODY="${out%$'\n'*}"
}

gh_ok() { [[ "$GH_STATUS" =~ ^2[0-9][0-9]$ ]]; }

# Reads GH_BODY, so it must run after gh_api and never wrap it.
json_field() { printf '%s' "$GH_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get(sys.argv[1],"") if isinstance(d,dict) else "")' "$1" 2>/dev/null || true; }

# ---------------------------------------------------------------- preflight --
say "Preflight"
[[ -n "${GITHUB_TOKEN:-}" ]] || die "GITHUB_TOKEN is unset."
command -v curl   >/dev/null || die "curl not found."
command -v python3>/dev/null || die "python3 not found."

gh_api GET "/repos/${REPO}"
gh_ok || die "cannot read ${REPO} (HTTP ${GH_STATUS}) -- check the token's repo access."
ok "GitHub token can read ${REPO}"

HAVE_AZ=1
if ! command -v az >/dev/null; then
  HAVE_AZ=0
  warn "az CLI not found -- Entra federated credential and role assignment will be skipped."
elif ! az account show >/dev/null 2>&1; then
  HAVE_AZ=0
  warn "az CLI is not logged in (\`az login\`) -- Azure phases will be skipped."
else
  ok "az CLI authenticated as $(az account show --query user.name -o tsv 2>/dev/null)"
fi

(( APPLY )) || warn "DRY RUN -- re-run with --apply to make changes."

# ---------------------------------------------------------------- variables --
# Checklist 1-5.
set_variable() {
  local key="$1" value="$2" payload current
  if [[ -z "$value" ]]; then
    warn "${key} not provided (export ${key}=...) -- skipped"
    return
  fi
  payload="$(python3 -c 'import json,sys; print(json.dumps({"name":sys.argv[1],"value":sys.argv[2]}))' "$key" "$value")"
  gh_api GET "/repos/${REPO}/actions/variables/${key}"
  local exists="$GH_STATUS"
  current="$(json_field value)"
  if [[ "$exists" == "200" && "$current" == "$value" ]]; then
    ok "${key} already set"
    return
  fi
  if (( ! APPLY )); then
    if [[ "$exists" == "200" ]]; then
      skip "PATCH /repos/${REPO}/actions/variables/${key}  (${current} -> ${value})"
    else
      skip "POST  /repos/${REPO}/actions/variables       (${key}=${value})"
    fi
    return
  fi
  if [[ "$exists" == "200" ]]; then
    gh_api PATCH "/repos/${REPO}/actions/variables/${key}" "$payload"
  else
    gh_api POST "/repos/${REPO}/actions/variables" "$payload"
  fi
  gh_ok || die "could not write variable ${key} (HTTP ${GH_STATUS})"
  ok "${key} set"
}

if step_wanted variables; then
  say "Repository variables"
  set_variable AZURE_CLIENT_ID       "${AZURE_CLIENT_ID:-}"
  set_variable AZURE_TENANT_ID       "${AZURE_TENANT_ID:-}"
  set_variable AZURE_SUBSCRIPTION_ID "${AZURE_SUBSCRIPTION_ID:-}"
  set_variable AZURE_FUNCTIONAPP_NAME "${AZURE_FUNCTIONAPP_NAME:-}"

  # The package path only needs to be set when it differs from the workflow's
  # own default, so read the workflow and confirm rather than blindly writing.
  gh_api GET "/repos/${REPO}/contents/.github/workflows/${WORKFLOW_FILE}?ref=${WORKFLOW_REF}"
  if gh_ok; then
    wf_text="$(printf '%s' "$GH_BODY" | python3 -c 'import base64,json,sys; print(base64.b64decode(json.load(sys.stdin).get("content","")).decode("utf-8","replace"))')"
    wf_default="$(printf '%s' "$wf_text" | sed -n 's/.*AZURE_FUNCTIONAPP_PACKAGE_PATH[": ]*[:=][ "'\'']*\([^"'\'' ]*\).*/\1/p' | head -1)"
    if [[ -n "$wf_default" ]]; then
      ok "workflow default package path: ${wf_default}"
    fi
    if [[ "$PACKAGE_PATH" != "api" || ( -n "$wf_default" && "$wf_default" != "$PACKAGE_PATH" ) ]]; then
      set_variable AZURE_FUNCTIONAPP_PACKAGE_PATH "$PACKAGE_PATH"
    else
      ok "AZURE_FUNCTIONAPP_PACKAGE_PATH left at the default (api)"
    fi
    # Checklist 9 depends on the workflow actually being OIDC-shaped.
    grep -q 'id-token: *write'     <<<"$wf_text" || warn "${WORKFLOW_FILE} is missing 'permissions: id-token: write' -- OIDC login will fail."
    grep -q 'azure/login'          <<<"$wf_text" || warn "${WORKFLOW_FILE} does not use azure/login -- nothing will consume the federated credential."
    grep -q "environment:" <<<"$wf_text"         || warn "${WORKFLOW_FILE} declares no environment -- the ${ENVIRONMENT}-scoped subject will not match."
    grep -q 'publish-profile'      <<<"$wf_text" && warn "${WORKFLOW_FILE} still references publish-profile -- remove it before step 10."
  else
    warn "could not read .github/workflows/${WORKFLOW_FILE} (HTTP ${GH_STATUS}) -- skipping package-path confirmation"
  fi
fi

# ----------------------------------------------------- federated credential --
# Checklist 6-7: one credential, subject pinned to the protected environment.
if step_wanted federation; then
  say "Entra federated identity credential"
  if (( ! HAVE_AZ )); then
    warn "skipped (no authenticated az CLI)"
  elif [[ -z "${AZURE_CLIENT_ID:-}" ]]; then
    warn "AZURE_CLIENT_ID unset -- cannot locate the app registration"
  else
    cred_name="${FEDERATED_CREDENTIAL_NAME:-github-${NAME}-${ENVIRONMENT}}"
    existing="$(az ad app federated-credential list --id "$AZURE_CLIENT_ID" \
                  --query "[?subject=='${SUBJECT}'].name" -o tsv 2>/dev/null || true)"
    if [[ -n "$existing" ]]; then
      ok "credential '${existing}' already binds ${SUBJECT}"
    elif (( ! APPLY )); then
      skip "az ad app federated-credential create --id ${AZURE_CLIENT_ID} --subject ${SUBJECT}"
    else
      params="$(python3 -c 'import json,sys; print(json.dumps({"name":sys.argv[1],"issuer":sys.argv[2],"subject":sys.argv[3],"audiences":[sys.argv[4]],"description":"GitHub Actions OIDC, environment-scoped"}))' \
        "$cred_name" "$FEDERATED_ISSUER" "$SUBJECT" "$FEDERATED_AUDIENCE")"
      az ad app federated-credential create --id "$AZURE_CLIENT_ID" --parameters "$params" >/dev/null \
        || die "federated credential creation failed"
      ok "credential '${cred_name}' created for ${SUBJECT}"
    fi

    # A federated credential only proves identity; the app still needs rights on
    # the function app or the deploy step fails with an authorization error.
    if [[ -n "$RESOURCE_GROUP" && -n "${AZURE_FUNCTIONAPP_NAME:-}" && -n "${AZURE_SUBSCRIPTION_ID:-}" ]]; then
      scope="/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${AZURE_FUNCTIONAPP_NAME}"
      assigned="$(az role assignment list --assignee "$AZURE_CLIENT_ID" --scope "$scope" \
                    --query "[?roleDefinitionName=='${ROLE}'].id" -o tsv 2>/dev/null || true)"
      if [[ -n "$assigned" ]]; then
        ok "${ROLE} already assigned on ${AZURE_FUNCTIONAPP_NAME}"
      elif (( ! APPLY )); then
        skip "az role assignment create --assignee ${AZURE_CLIENT_ID} --role ${ROLE} --scope ${scope}"
      else
        az role assignment create --assignee "$AZURE_CLIENT_ID" --role "$ROLE" --scope "$scope" >/dev/null \
          || die "role assignment failed"
        ok "${ROLE} assigned on ${AZURE_FUNCTIONAPP_NAME}"
      fi
    else
      warn "AZURE_RESOURCE_GROUP / AZURE_FUNCTIONAPP_NAME / AZURE_SUBSCRIPTION_ID incomplete -- role assignment skipped"
    fi
  fi
fi

# -------------------------------------------------------------- environment --
# Checklist 8: the environment gate is what makes the pinned subject meaningful.
if step_wanted environment; then
  say "Protected environment '${ENVIRONMENT}'"
  reviewers_json="[]"
  if [[ -n "$REQUIRED_REVIEWERS" ]]; then
    ids=()
    IFS=',' read -ra entries <<<"$REQUIRED_REVIEWERS"
    for entry in "${entries[@]}"; do
      entry="${entry// /}"
      case "$entry" in
        team:*)
          slug="${entry#team:}"
          gh_api GET "/orgs/${OWNER}/teams/${slug}"
          if gh_ok; then ids+=("{\"type\":\"Team\",\"id\":$(json_field id)}")
          else warn "team ${slug} not found (HTTP ${GH_STATUS})"; fi
          ;;
        *)
          login="${entry#user:}"
          gh_api GET "/users/${login}"
          if gh_ok; then ids+=("{\"type\":\"User\",\"id\":$(json_field id)}")
          else warn "user ${login} not found (HTTP ${GH_STATUS})"; fi
          ;;
      esac
    done
    (( ${#ids[@]} )) || die "none of the REQUIRED_REVIEWERS could be resolved"
    reviewers_json="[$(IFS=,; echo "${ids[*]}")]"
  fi

  gh_api GET "/repos/${REPO}/environments/${ENVIRONMENT}"
  current_reviewers="$(printf '%s' "$GH_BODY" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: raise SystemExit
for r in d.get("protection_rules",[]) or []:
    if r.get("type")=="required_reviewers":
        print(len(r.get("reviewers",[])))' 2>/dev/null || true)"

  if [[ -z "$REQUIRED_REVIEWERS" ]]; then
    if [[ -n "$current_reviewers" && "$current_reviewers" != "0" ]]; then
      ok "${ENVIRONMENT} already has ${current_reviewers} required reviewer(s)"
    else
      warn "REQUIRED_REVIEWERS unset and ${ENVIRONMENT} has none -- set REQUIRED_REVIEWERS='user:login,team:slug'"
    fi
  else
    body="$(python3 -c 'import json,sys; print(json.dumps({"reviewers":json.loads(sys.argv[1]),"deployment_branch_policy":None,"wait_timer":0}))' "$reviewers_json")"
    if (( ! APPLY )); then
      skip "PUT /repos/${REPO}/environments/${ENVIRONMENT}  reviewers=${reviewers_json}"
    else
      gh_api PUT "/repos/${REPO}/environments/${ENVIRONMENT}" "$body"
      gh_ok || die "could not protect ${ENVIRONMENT} (HTTP ${GH_STATUS})"
      ok "${ENVIRONMENT} protected with required reviewers"
    fi
  fi
fi

# ------------------------------------------------------------------- verify --
# Checklist 9: a manual run is the only proof the federation actually works.
if step_wanted verify; then
  say "Workflow run"
  if (( ! APPLY )); then
    skip "POST /repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches  ref=${WORKFLOW_REF}"
  else
    body="$(python3 -c 'import json,sys; print(json.dumps({"ref":sys.argv[1]}))' "$WORKFLOW_REF")"
    gh_api POST "/repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches" "$body"
    gh_ok || die "workflow_dispatch failed (HTTP ${GH_STATUS}) -- the workflow needs a workflow_dispatch trigger"
    ok "dispatched ${WORKFLOW_FILE} on ${WORKFLOW_REF}"
    echo "         watch: https://github.com/${REPO}/actions/workflows/${WORKFLOW_FILE}"
    warn "the run will pause for required-reviewer approval before it deploys -- approve it, then re-run --step cleanup"
  fi
fi

# ------------------------------------------------------------------ cleanup --
# Checklist 10: only after a green OIDC run -- deleting the publish profile
# while it is still the only working credential takes production down.
if step_wanted cleanup; then
  say "Retire ${PUBLISH_PROFILE_SECRET}"
  gh_api GET "/repos/${REPO}/actions/secrets/${PUBLISH_PROFILE_SECRET}"
  if [[ "$GH_STATUS" == "404" ]]; then
    ok "${PUBLISH_PROFILE_SECRET} already removed"
  else
    gh_api GET "/repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=1&status=success"
    latest="$(printf '%s' "$GH_BODY" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: raise SystemExit
runs=d.get("workflow_runs") or []
print(runs[0]["html_url"] if runs else "")' 2>/dev/null || true)"
    if [[ -z "$latest" ]]; then
      warn "no successful ${WORKFLOW_FILE} run found -- refusing to delete the last working credential"
    elif (( ! APPLY )); then
      skip "DELETE /repos/${REPO}/actions/secrets/${PUBLISH_PROFILE_SECRET}  (last green run: ${latest})"
    else
      gh_api DELETE "/repos/${REPO}/actions/secrets/${PUBLISH_PROFILE_SECRET}"
      gh_ok || die "could not delete ${PUBLISH_PROFILE_SECRET} (HTTP ${GH_STATUS})"
      ok "${PUBLISH_PROFILE_SECRET} deleted -- OIDC is now the only deployment path"
    fi
  fi
fi

say "Done"
(( APPLY )) || echo "   (dry run -- nothing was changed)"
