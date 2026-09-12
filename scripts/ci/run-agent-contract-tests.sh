#!/usr/bin/env sh
set -eu
# run-agent-contract-tests.sh — non-destructive agent contract checks. Runs with
# DRY_RUN=true and SANDBOX_MODE=true so nothing mutates state. Startup, schema,
# and health checks are placeholders until agents expose a dry-run harness; the
# one real check is that any committed agent.json parses as valid JSON. Evidence
# is written to artifacts/evidence/agent-contract-tests.json.

export DRY_RUN=true
export SANDBOX_MODE=true

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EVIDENCE_DIR="$ROOT/artifacts/evidence"
mkdir -p "$EVIDENCE_DIR"
OUT="$EVIDENCE_DIR/agent-contract-tests.json"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

SCHEMA_STATUS="skipped"
if [ -d "$ROOT/agents" ]; then
  SCHEMA_STATUS="checked"
  # Validate every committed agent.json is well-formed (read-only).
  find "$ROOT/agents" -name 'agent.json' 2>/dev/null | while IFS= read -r j; do
    python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$j" \
      || { echo "run-agent-contract-tests: FAIL: invalid JSON $j" >&2; exit 1; }
  done
fi

cat > "$OUT" <<EOF
{
  "generated_at": "$TS",
  "dry_run": true,
  "sandbox_mode": true,
  "checks": {
    "startup": "placeholder",
    "schema": "placeholder",
    "schema_json_validation": "$SCHEMA_STATUS",
    "health": "placeholder"
  },
  "status": "PASS"
}
EOF

echo "run-agent-contract-tests: wrote $OUT"
cat "$OUT"
