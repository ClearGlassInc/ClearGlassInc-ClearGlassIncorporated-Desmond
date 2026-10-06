#!/usr/bin/env bash
# deploy_target.sh — the one place the deploy workflows talk to a cloud.
#
# reusable-deploy.yml calls these actions and never a cloud CLI directly, so
# moving off Cloud Run means implementing the same five actions for another
# provider, not rewriting workflows:
#
#   describe   exists, url, serving_revision (the revision holding 100% traffic)
#   deploy     IMAGE -> new revision with NO traffic, reachable at a tag URL
#                -> revision, candidate_url
#   promote    route 100% of traffic to REVISION -> url
#   rollback   route 100% of traffic to REVISION (the one describe reported)
#   untag      remove TAG (preview teardown, candidate-tag cleanup)
#
# Inputs are environment variables (never interpolated into a shell string):
#   DEPLOY_PROVIDER  cloudrun (implemented) | ecs | kubernetes (fail closed)
#   DEPLOY_PROJECT   cloud project/account     DEPLOY_REGION  region
#   SERVICE IMAGE TAG REVISION PORT
#   ENV_VARS         comma-separated KEY=VALUE merged into the new revision
#                    (merge, never replace: staging/production keep the
#                    configuration and secret references set on the service)
#   COMMIT_SHA       recorded as a revision label
#
# Outputs go to $GITHUB_OUTPUT when set, else stdout, as key=value lines.
set -euo pipefail

action="${1:-}"
provider="${DEPLOY_PROVIDER:-}"

out() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "$1=$2" >> "$GITHUB_OUTPUT"; fi
  echo "$1=$2"
}

die() {
  echo "::error title=deploy_target ${action:-?}::$*" >&2
  exit 1
}

need() {
  local name
  for name in "$@"; do
    [ -n "${!name:-}" ] || die "$name is required for '$action'"
  done
}

# ── Cloud Run ──────────────────────────────────────────────────────────────

gc() { gcloud "$@" --project "$DEPLOY_PROJECT" --region "$DEPLOY_REGION" --quiet; }

cr_describe_json() { gc run services describe "$SERVICE" --format=json 2>/dev/null; }

cloudrun_describe() {
  need DEPLOY_PROJECT DEPLOY_REGION SERVICE
  local json
  if ! json="$(cr_describe_json)"; then
    out exists false
    out url ""
    out serving_revision ""
    return 0
  fi
  out exists true
  out url "$(jq -r '.status.url // ""' <<<"$json")"
  out serving_revision "$(jq -r '[.status.traffic[]? | select(.percent == 100) | .revisionName][0] // ""' <<<"$json")"
}

cloudrun_deploy() {
  need DEPLOY_PROJECT DEPLOY_REGION SERVICE IMAGE TAG PORT
  # Revision tags: lowercase letters, digits and hyphens.
  [[ "$TAG" =~ ^[a-z][a-z0-9-]{0,45}$ ]] || die "invalid revision tag '$TAG'"
  # The service must already exist: an implicit create would pick IAM, ingress
  # and scaling defaults nobody reviewed, and would have no previous revision
  # to roll back to.
  cr_describe_json > /dev/null || die "service '$SERVICE' does not exist in $DEPLOY_PROJECT/$DEPLOY_REGION; create it once by hand (AUTOMATION.md, 'Bootstrap')"

  local args=(run deploy "$SERVICE" --image "$IMAGE" --tag "$TAG" --no-traffic --port "$PORT"
              --labels "managed-by=github-actions,commit-sha=${COMMIT_SHA:-unknown}")
  if [ -n "${ENV_VARS:-}" ]; then args+=(--update-env-vars "$ENV_VARS"); fi
  gc "${args[@]}"

  local json
  json="$(cr_describe_json)" || die "service vanished after deploy"
  out revision "$(jq -r '.status.latestCreatedRevisionName // ""' <<<"$json")"
  out candidate_url "$(jq -r --arg tag "$TAG" '[.status.traffic[]? | select(.tag == $tag) | .url][0] // ""' <<<"$json")"
}

cloudrun_route() {
  need DEPLOY_PROJECT DEPLOY_REGION SERVICE REVISION
  gc run services update-traffic "$SERVICE" --to-revisions "${REVISION}=100"
  out url "$(cr_describe_json | jq -r '.status.url // ""')"
}

cloudrun_untag() {
  need DEPLOY_PROJECT DEPLOY_REGION SERVICE TAG
  if ! cr_describe_json | jq -e --arg tag "$TAG" 'any(.status.traffic[]?; .tag == $tag)' > /dev/null; then
    echo "tag '$TAG' is not on $SERVICE; nothing to remove"
    return 0
  fi
  gc run services update-traffic "$SERVICE" --remove-tags "$TAG"
}

# ── dispatch ───────────────────────────────────────────────────────────────

case "$provider" in
  cloudrun)
    command -v gcloud > /dev/null || die "gcloud is not installed"
    command -v jq > /dev/null || die "jq is not installed"
    case "$action" in
      describe) cloudrun_describe ;;
      deploy) cloudrun_deploy ;;
      promote | rollback) cloudrun_route ;;
      untag) cloudrun_untag ;;
      *) die "unknown action '$action' (describe|deploy|promote|rollback|untag)" ;;
    esac
    ;;
  ecs | kubernetes)
    die "provider '$provider' is not implemented. Implement describe/deploy/promote/rollback/untag for it in scripts/ci/deploy_target.sh (AUTOMATION.md, 'Adding a provider')"
    ;;
  "")
    die "DEPLOY_PROVIDER is not set"
    ;;
  *)
    die "unknown provider '$provider'"
    ;;
esac
