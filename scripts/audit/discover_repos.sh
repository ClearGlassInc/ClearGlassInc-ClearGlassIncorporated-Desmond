#!/usr/bin/env bash
# Discover all repos owned by a GitHub org/user and write repo_list.txt.
#
# Usage:
#   GH_OWNER=ClearGlassInc ./discover_repos.sh           # org
#   GH_OWNER=@me           ./discover_repos.sh           # current user
#
# Outputs (in $OUT_DIR, default ./audit-out):
#   all_repos.json    -- full gh repo list JSON
#   repo_list.txt     -- one "owner/name" per line, archived excluded
#
# Requires: gh (authenticated), jq.
set -euo pipefail

OWNER="${GH_OWNER:?set GH_OWNER (e.g. ClearGlassInc or @me)}"
OUT_DIR="${OUT_DIR:-./audit-out}"
LIMIT="${LIMIT:-1000}"

mkdir -p "$OUT_DIR"

command -v gh >/dev/null || { echo "gh CLI not installed" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq not installed" >&2; exit 2; }

gh auth status >/dev/null 2>&1 || { echo "gh not authenticated; run: gh auth login" >&2; exit 2; }

echo "[discover] listing repos for owner=$OWNER limit=$LIMIT"
if [[ "$OWNER" == "@me" ]]; then
  gh repo list --limit "$LIMIT" \
    --json name,owner,url,isArchived,isFork,defaultBranchRef,visibility \
    > "$OUT_DIR/all_repos.json"
else
  gh repo list "$OWNER" --limit "$LIMIT" \
    --json name,owner,url,isArchived,isFork,defaultBranchRef,visibility \
    > "$OUT_DIR/all_repos.json"
fi

jq -r '.[] | select(.isArchived == false) | "\(.owner.login)/\(.name)"' \
  "$OUT_DIR/all_repos.json" | sort -u > "$OUT_DIR/repo_list.txt"

count=$(wc -l < "$OUT_DIR/repo_list.txt" | tr -d ' ')
echo "[discover] wrote $OUT_DIR/repo_list.txt ($count active repos)"
