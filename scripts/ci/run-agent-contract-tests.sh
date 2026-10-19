#!/usr/bin/env sh
set -eu
# Non-destructive agent contract preflight.
# This validates agent.json syntax only; it does NOT start agents or verify
# runtime health. Keep evidence explicit so schema validation cannot be
# mistaken for operational agent activation.

export DRY_RUN=true
export SANDBOX_MODE=true

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EVIDENCE_DIR="$ROOT/artifacts/evidence"
mkdir -p "$EVIDENCE_DIR"
OUT="$EVIDENCE_DIR/agent-contract-tests.json"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

AGENT_DIR_STATUS="not_found"
SCHEMA_STATUS="not_applicable"
AGENT_COUNT=0

if [ -d "$ROOT/agents" ]; then
  AGENT_DIR_STATUS="found"
  AGENT_COUNT="$(find "$ROOT/agents" -type f -name 'agent.json' -print | wc -l | tr -d ' ')"
  if [ "$AGENT_COUNT" -gt 0 ]; then
    # find -exec propagates a validator failure; avoid a pipeline whose
    # while-loop/subshell could hide a failed JSON parse from the parent shell.
    find "$ROOT/agents" -type f -name 'agent.json' -exec python3 -c '
import json
import pathlib
import sys

for raw_path in sys.argv[1:]:
    path = pathlib.Path(raw_path)
    try:
        with path.open(encoding="utf-8") as stream:
            json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"agent-contract-tests: FAIL: {path}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(f"agent-contract-tests: valid JSON: {path}")
' {} +
    SCHEMA_STATUS="passed"
  else
    SCHEMA_STATUS="no_agent_json_files"
  fi
fi

# Runtime startup and health checks remain unimplemented until agent packages
# expose stable, safe test entry points. Never label those checks as passed.
cat > "$OUT" <<EOF
{
  "generated_at": "$TS",
  "dry_run": true,
  "sandbox_mode": true,
  "scope": "agent configuration JSON syntax only",
  "agent_directory": "$AGENT_DIR_STATUS",
  "agent_json_files_found": $AGENT_COUNT,
  "checks": {
    "schema_json_validation": "$SCHEMA_STATUS",
    "startup": "not_implemented",
    "health": "not_implemented",
    "integration_execution": "not_implemented"
  },
  "status": "PARTIAL",
  "limitations": [
    "This script does not launch agents.",
    "This script does not prove agent readiness, integration, or live operation."
  ]
}
EOF

echo "run-agent-contract-tests: configuration preflight complete; runtime activation is NOT VERIFIED"
echo "run-agent-contract-tests: evidence: $OUT"
cat "$OUT"
