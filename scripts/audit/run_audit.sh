#!/usr/bin/env bash
# One-shot orchestrator: discover -> audit -> aggregate.
#
# Usage:
#   GH_OWNER=ClearGlassInc ./run_audit.sh
#   GH_OWNER=ClearGlassInc PARALLEL=4 SKIP_DEPS=1 ./run_audit.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
: "${GH_OWNER:?set GH_OWNER}"

"$HERE/discover_repos.sh"
"$HERE/audit_all.sh"
python3 "$HERE/aggregate_report.py"
echo "[run_audit] complete. See ./audit-out/audit_report.{csv,md}"
