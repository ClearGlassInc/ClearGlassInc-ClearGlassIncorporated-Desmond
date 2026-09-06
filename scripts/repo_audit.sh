#!/usr/bin/env bash
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#
# ClearGlass multi-repo audit — discovery + audit driver.
#
# Auth model (deliberate): the GitHub token is read from the GITHUB_TOKEN
# environment variable only. This script never reads ~/.github_token and never
# runs `gh auth login` — keep credentials in your shell env or CI secrets:
#
#     export GITHUB_TOKEN=ghp_xxx        # a token scoped to the org, read-only
#     scripts/repo_audit.sh ClearGlassInc
#
# With no argument it runs a self-audit of the current checkout (no network).
set -euo pipefail

OWNER="${1:-}"
OUT_DIR="${OUT_DIR:-audit-reports}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "$OWNER" ]]; then
  echo "→ No owner given — running self-audit of $(basename "$ROOT") (offline)."
  python3 scripts/repo_audit.py --self --out "$OUT_DIR"
  exit 0
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export an org-scoped read token first." >&2
  echo "       export GITHUB_TOKEN=...   (this script never reads token files)" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

# ── discovery: prefer gh if present, else the REST API via curl ──────────────
echo "→ Discovering repositories for '$OWNER'…"
if command -v gh >/dev/null 2>&1; then
  gh repo list "$OWNER" --limit 1000 --json name,owner,url,isArchived \
    > "$OUT_DIR/all_repos.json"
  jq -r '.[] | select(.isArchived|not) | .name' "$OUT_DIR/all_repos.json" \
    > "$OUT_DIR/repo_list.txt"
else
  echo "  gh not found — using REST API via curl."
  page=1; : > "$OUT_DIR/all_repos.json.tmp"
  while :; do
    resp="$(curl -fsS \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json" \
      "$API_BASE/orgs/$OWNER/repos?per_page=100&page=$page" 2>/dev/null \
      || curl -fsS \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json" \
      "${API_BASE:-https://api.github.com}/users/$OWNER/repos?per_page=100&page=$page")"
    count="$(echo "$resp" | jq 'length')"
    echo "$resp" | jq -r '.[] | select(.archived|not) | .name' >> "$OUT_DIR/repo_list.txt"
    [[ "$count" -lt 100 ]] && break
    page=$((page+1))
  done
fi

n="$(wc -l < "$OUT_DIR/repo_list.txt" | tr -d ' ')"
echo "→ $n repositories discovered. Auditing…"

# ── audit: the Python auditor does the per-repo API work + scoring ───────────
python3 scripts/repo_audit.py --org "$OWNER" --out "$OUT_DIR"

echo "→ Reports written to $OUT_DIR/repo_audit.csv and $OUT_DIR/repo_audit.json"
