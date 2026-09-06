#!/usr/bin/env bash
# Loop repo_list.txt and run audit_repo.sh on each, with optional parallelism.
#
# Usage:
#   ./audit_all.sh                       # reads ./audit-out/repo_list.txt
#   PARALLEL=4 ./audit_all.sh             # 4 repos at a time
#   REPO_LIST=./mine.txt ./audit_all.sh
#
# Env passed through to audit_repo.sh: OUT_DIR, CLONE_DIR, BOT_WINDOW,
#                                      SKIP_DEPS, SKIP_CLONE, KEEP_CLONES.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_LIST="${REPO_LIST:-./audit-out/repo_list.txt}"
PARALLEL="${PARALLEL:-2}"

[[ -f "$REPO_LIST" ]] || { echo "missing $REPO_LIST (run discover_repos.sh first)" >&2; exit 2; }

total="$(wc -l < "$REPO_LIST" | tr -d ' ')"
echo "[audit_all] $total repos, parallelism=$PARALLEL"

# Run with xargs -P for portable parallelism.
xargs -P "$PARALLEL" -I {} bash -c '
  set -e
  "$0" "$1" || echo "[audit_all] FAILED: $1" >&2
' "$HERE/audit_repo.sh" < "$REPO_LIST"

echo "[audit_all] done. Aggregate with: python3 $HERE/aggregate_report.py"
