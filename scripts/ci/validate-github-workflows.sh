#!/usr/bin/env sh
set -eu
# validate-github-workflows.sh — parse every .github/workflows/*.yml with
# PyYAML and flag actions pinned to a moving ref (@main / @master). Findings are
# written to artifacts/evidence/workflow-integrity.json. Parse errors fail
# closed; unpinned-action findings are recorded but non-fatal in scaffolding.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EVIDENCE_DIR="$ROOT/artifacts/evidence"
mkdir -p "$EVIDENCE_DIR"
OUT="$EVIDENCE_DIR/workflow-integrity.json"

python3 - "$ROOT" "$OUT" <<'PY'
import datetime
import glob
import json
import os
import sys

root, out = sys.argv[1], sys.argv[2]

try:
    import yaml
except ImportError:
    print("validate-github-workflows: FAIL: PyYAML not installed", file=sys.stderr)
    sys.exit(1)

wf_dir = os.path.join(root, ".github", "workflows")
files = sorted(
    glob.glob(os.path.join(wf_dir, "*.yml"))
    + glob.glob(os.path.join(wf_dir, "*.yaml"))
)

parse_errors = []
unpinned = []
for path in files:
    rel = os.path.relpath(path, root)
    try:
        with open(path) as fh:
            yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001
        parse_errors.append({"file": rel, "error": str(exc)})
        continue
    with open(path) as fh:
        for lineno, line in enumerate(fh, 1):
            stripped = line.strip()
            if stripped.startswith("- uses:") or stripped.startswith("uses:"):
                ref = stripped.split("uses:", 1)[1].strip().strip('"\'')
                if ref.endswith("@main") or ref.endswith("@master"):
                    unpinned.append({"file": rel, "line": lineno, "uses": ref})

report = {
    "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "workflows_scanned": len(files),
    "parse_errors": parse_errors,
    "unpinned_actions": unpinned,
    "status": "PASS" if not parse_errors and not unpinned else "FINDINGS",
}

os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as fh:
    json.dump(report, fh, indent=2)

print(json.dumps(report, indent=2))

if parse_errors:
    sys.exit(1)
PY

echo "validate-github-workflows: wrote $OUT"
