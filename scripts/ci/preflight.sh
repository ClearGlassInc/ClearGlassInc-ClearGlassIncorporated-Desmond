#!/usr/bin/env sh
set -eu
# preflight.sh — validate pipeline parameter combinations and fail closed on an
# invalid or unsafe configuration before any deploy job is reached.

RUN_VALIDATION="${RUN_VALIDATION:-true}"
DEPLOY_STAGING="${DEPLOY_STAGING:-false}"
DEPLOY_PRODUCTION="${DEPLOY_PRODUCTION:-false}"
DRY_RUN="${DRY_RUN:-true}"

fail() { echo "preflight: FAIL: $1" >&2; exit 1; }

echo "preflight: run_validation=$RUN_VALIDATION deploy_staging=$DEPLOY_STAGING deploy_production=$DEPLOY_PRODUCTION dry_run=$DRY_RUN"

# A single pipeline must not target both environments at once.
if [ "$DEPLOY_STAGING" = "true" ] && [ "$DEPLOY_PRODUCTION" = "true" ]; then
  fail "deploy_staging and deploy_production are mutually exclusive; run one target per pipeline"
fi

# Production deploys require the validation gate to have run.
if [ "$DEPLOY_PRODUCTION" = "true" ] && [ "$RUN_VALIDATION" != "true" ]; then
  fail "deploy_production requires run_validation=true (validation gate must pass first)"
fi

# Staging deploys likewise require validation.
if [ "$DEPLOY_STAGING" = "true" ] && [ "$RUN_VALIDATION" != "true" ]; then
  fail "deploy_staging requires run_validation=true (validation gate must pass first)"
fi

echo "preflight: OK"
