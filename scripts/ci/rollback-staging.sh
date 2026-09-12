#!/usr/bin/env sh
set -eu
# rollback-staging.sh — restore staging to the last verified artifact.
#
# The rollback command is a REPLACE_ME placeholder: inert until a human wires
# the real rollback command and connects the staging-deploy context.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EVIDENCE_DIR="$ROOT/artifacts/evidence"
PREV_FILE="$EVIDENCE_DIR/staging-previous-version.txt"

if [ -f "$PREV_FILE" ]; then
  PREV="$(cat "$PREV_FILE")"
  echo "rollback-staging: restoring previous verified staging version: $PREV"
else
  echo "rollback-staging: WARN: no captured previous version; falling back to last verified artifact" >&2
fi

echo "rollback-staging: executing rollback"
REPLACE_ME_ROLLBACK_COMMAND

echo "rollback-staging: OK"
