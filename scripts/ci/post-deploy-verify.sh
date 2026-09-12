#!/usr/bin/env sh
set -eu
# post-deploy-verify.sh <staging|production> — verify a deployed environment:
# HTTPS reachability, HTTP status, and a release marker in the response body.
# Writes evidence to artifacts/evidence/. Endpoints come from context env vars
# (STAGING_URL / PRODUCTION_URL); nothing is hardcoded.

TARGET="${1:-}"
case "$TARGET" in
  staging)    URL="${STAGING_URL:-}" ;;
  production) URL="${PRODUCTION_URL:-}" ;;
  *) echo "post-deploy-verify: FAIL: usage: post-deploy-verify.sh <staging|production>" >&2; exit 2 ;;
esac

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EVIDENCE_DIR="$ROOT/artifacts/evidence"
mkdir -p "$EVIDENCE_DIR"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUT="$EVIDENCE_DIR/${TARGET}-verify.json"

STATUS="unknown"
HTTP_CODE="000"
MARKER="unchecked"

if [ -n "$URL" ]; then
  case "$URL" in
    https://*) ;;
    *) echo "post-deploy-verify: FAIL: ${TARGET} URL must be HTTPS" >&2; exit 1 ;;
  esac
  if command -v curl >/dev/null 2>&1; then
    BODY="$(mktemp)"
    HTTP_CODE="$(curl -s -o "$BODY" -w '%{http_code}' --max-time 20 "$URL" || echo 000)"
    if [ "$HTTP_CODE" = "200" ]; then STATUS="reachable"; else STATUS="degraded"; fi
    if grep -q "${RELEASE_MARKER:-__no_release_marker__}" "$BODY" 2>/dev/null; then
      MARKER="present"
    else
      MARKER="absent"
    fi
    rm -f "$BODY"
  else
    STATUS="skipped-no-curl"
  fi
else
  STATUS="skipped-no-url"
fi

cat > "$OUT" <<EOF
{
  "generated_at": "$TS",
  "target": "$TARGET",
  "url_configured": $( [ -n "$URL" ] && echo true || echo false ),
  "http_status": "$HTTP_CODE",
  "reachability": "$STATUS",
  "release_marker": "$MARKER"
}
EOF

echo "post-deploy-verify: wrote $OUT"
cat "$OUT"

# Fail closed only when a URL was configured but the environment is unreachable.
if [ -n "$URL" ] && [ "$STATUS" = "degraded" ]; then
  echo "post-deploy-verify: FAIL: ${TARGET} unreachable or non-200" >&2
  exit 1
fi
