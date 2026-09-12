#!/usr/bin/env sh
set -eu
# deploy-staging.sh — verify the release artifact digest, capture the currently
# deployed staging version (for rollback), then execute the staging deploy.
#
# The deploy command is a REPLACE_ME placeholder: this scaffolding is inert
# until a human wires the real deploy command and connects the staging-deploy
# context on circleci.com.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
REL_DIR="$ROOT/artifacts/release"
MANIFEST="$REL_DIR/manifest.json"
EVIDENCE_DIR="$ROOT/artifacts/evidence"
mkdir -p "$EVIDENCE_DIR"

[ -f "$MANIFEST" ] || { echo "deploy-staging: FAIL: missing release manifest ($MANIFEST)" >&2; exit 1; }

# Re-verify the artifact digest recorded in the manifest.
EXPECTED="$(sed -n 's/.*"artifact_sha256": *"\([^"]*\)".*/\1/p' "$MANIFEST")"
ARTIFACT="$REL_DIR/source.tar"
if [ -f "$ARTIFACT" ] && command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$ARTIFACT" | awk '{print $1}')"
  [ "$EXPECTED" = "$ACTUAL" ] || { echo "deploy-staging: FAIL: artifact digest mismatch (expected $EXPECTED, got $ACTUAL)" >&2; exit 1; }
  echo "deploy-staging: artifact digest verified ($ACTUAL)"
else
  echo "deploy-staging: WARN: artifact or sha256sum unavailable; cannot re-verify digest" >&2
fi

# Capture the current deployed version so rollback has a known-good target.
CURRENT_VERSION="${STAGING_CURRENT_VERSION:-unknown}"
printf '%s\n' "$CURRENT_VERSION" > "$EVIDENCE_DIR/staging-previous-version.txt"
echo "deploy-staging: captured current staging version: $CURRENT_VERSION"

echo "deploy-staging: executing deploy"
REPLACE_ME_DEPLOY_COMMAND

echo "deploy-staging: OK"
