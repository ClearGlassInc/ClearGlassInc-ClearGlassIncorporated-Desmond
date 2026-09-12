#!/usr/bin/env sh
set -eu
# build-release-manifest.sh — produce an immutable release manifest describing
# exactly what would be deployed: git SHA, pipeline id, build time, artifact
# SHA-256 digest, and deployment target. The manifest is persisted to the
# CircleCI workspace so deploy jobs can verify the digest before shipping.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
OUT_DIR="$ROOT/artifacts/release"
mkdir -p "$OUT_DIR"

GIT_SHA="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
PIPELINE_ID="${CIRCLE_WORKFLOW_ID:-local}"
BUILD_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DEPLOY_TARGET="${DEPLOY_TARGET:-none}"

# Deterministic artifact = the tracked file tree at this commit.
ARTIFACT="$OUT_DIR/source.tar"
if ! git -C "$ROOT" archive --format=tar "$GIT_SHA" > "$ARTIFACT" 2>/dev/null; then
  tar -cf "$ARTIFACT" -C "$ROOT" .
fi

if command -v sha256sum >/dev/null 2>&1; then
  DIGEST="$(sha256sum "$ARTIFACT" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  DIGEST="$(shasum -a 256 "$ARTIFACT" | awk '{print $1}')"
else
  DIGEST="unavailable"
fi

MANIFEST="$OUT_DIR/manifest.json"
cat > "$MANIFEST" <<EOF
{
  "git_sha": "$GIT_SHA",
  "pipeline_id": "$PIPELINE_ID",
  "build_timestamp": "$BUILD_TS",
  "artifact": "source.tar",
  "artifact_sha256": "$DIGEST",
  "deploy_target": "$DEPLOY_TARGET"
}
EOF

echo "build-release-manifest: wrote $MANIFEST"
cat "$MANIFEST"
