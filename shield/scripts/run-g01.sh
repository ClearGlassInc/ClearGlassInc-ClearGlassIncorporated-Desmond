#!/usr/bin/env bash
# Shield G01: static checks, then two clean bootstrap -> test -> teardown -> verify-clean
# cycles. Every step runs even after a failure, so the evidence shows all of them; the
# exit code is non-zero if any test failed or any teardown left something behind.
set -uo pipefail
cd "$(dirname "$0")/../.."
ARTIFACT_DIR="${SHIELD_ARTIFACT_DIR:-artifacts/shield-g01}"
RUN_ID="${SHIELD_RUN_ID:-local-$(date -u +%Y%m%dT%H%M%SZ)}"
rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR"
printf '%s\n' "$RUN_ID" > "$ARTIFACT_DIR/run_id"
status=0
python3 -m shield.g01_suite static --artifacts "$ARTIFACT_DIR" --run-id "$RUN_ID" || status=1
for cycle in 1 2; do
  python3 -m shield.g01_suite cycle "$cycle" --artifacts "$ARTIFACT_DIR" --run-id "$RUN_ID" || status=1
  python3 -m shield.topology verify-clean > "$ARTIFACT_DIR/cycle-$cycle/verify-clean.json" || status=1
done
exit "$status"
