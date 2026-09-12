#!/usr/bin/env sh
set -eu
# rollback-production.sh — restore production to the last verified artifact.
#
# The rollback command is a REPLACE_ME placeholder: inert until a human wires
# the real rollback command and connects the production-deploy context.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EVIDENCE_DIR="$ROOT/artifacts/evidence"
PREV_FILE="$EVIDENCE_DIR/production-previous-version.txt"

if [ -f "$PREV_FILE" ]; then
  PREV="$(cat "$PREV_FILE")"
  echo "rollback-production: restoring previous verified production version: $PREV"
else
  echo "rollback-production: WARN: no captured previous version; falling back to last verified artifact" >&2
fi

echo "rollback-production: executing rollback"
REPLACE_ME_ROLLBACK_COMMAND

echo "rollback-production: OK"
