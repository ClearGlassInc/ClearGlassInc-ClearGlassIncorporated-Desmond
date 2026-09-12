#!/usr/bin/env sh
set -eu
# deploy-production.sh — verify the release artifact digest, capture the current
# production version (for rollback), then execute the production deploy.
#
# The deploy command is a REPLACE_ME placeholder: this scaffolding is inert
# until a human wires the real deploy command and connects the production-deploy
# context on circleci.com.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
REL_DIR="$ROOT/artifacts/release"
MANIFEST="$REL_DIR/manifest.json"
EVIDENCE_DIR="$ROOT/artifacts/evidence"
mkdir -p "$EVIDENCE_DIR"

[ -f "$MANIFEST" ] || { echo "deploy-production: FAIL: missing release manifest ($MANIFEST)" >&2; exit 1; }

# Re-verify the artifact digest recorded in the manifest.
EXPECTED="$(sed -n 's/.*"artifact_sha256": *"\([^"]*\)".*/\1/p' "$MANIFEST")"
ARTIFACT="$REL_DIR/source.tar"
if [ -f "$ARTIFACT" ] && command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$ARTIFACT" | awk '{print $1}')"
  [ "$EXPECTED" = "$ACTUAL" ] || { echo "deploy-production: FAIL: artifact digest mismatch (expected $EXPECTED, got $ACTUAL)" >&2; exit 1; }
  echo "deploy-production: artifact digest verified ($ACTUAL)"
else
  echo "deploy-production: WARN: artifact or sha256sum unavailable; cannot re-verify digest" >&2
fi

# Capture the current deployed version so rollback has a known-good target.
CURRENT_VERSION="${PRODUCTION_CURRENT_VERSION:-unknown}"
printf '%s\n' "$CURRENT_VERSION" > "$EVIDENCE_DIR/production-previous-version.txt"
echo "deploy-production: captured current production version: $CURRENT_VERSION"

echo "deploy-production: executing deploy"
REPLACE_ME_DEPLOY_COMMAND

echo "deploy-production: OK"
