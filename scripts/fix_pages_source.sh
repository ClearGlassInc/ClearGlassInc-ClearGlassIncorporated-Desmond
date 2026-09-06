#!/usr/bin/env bash
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#
# Fix failing "production" / GitHub Pages deployments.
#
# Root cause: while the Pages publishing Source stays "Deploy from a branch",
# GitHub keeps auto-triggering its legacy "pages build and deployment" pipeline
# on every push to main. That pipeline's deploy step fails with
#   "No artifacts named github-pages were found for this workflow run"
# (its build job uploads an artifact incompatible with deploy-pages@v5),
# leaving a red X on the Deployments page even though our own
# "Deploy GitHub Pages" workflow (.github/workflows/pages.yml) deploys fine.
#
# The permanent fix is to set the Pages build_type to "workflow" (i.e. Source =
# "GitHub Actions"). That requires an ADMIN-scoped token — the default Actions
# GITHUB_TOKEN is rejected with HTTP 403 — so this one-time step is run by an
# operator (or wired up as the PAGES_ADMIN_TOKEN secret consumed by pages.yml).
#
# Auth model (same as scripts/repo_audit.sh): the token is read from the
# GITHUB_TOKEN environment variable only. Use a fine-grained PAT with the
# "Pages" (write) and repo "Administration" permissions:
#
#     export GITHUB_TOKEN=github_pat_xxx
#     scripts/fix_pages_source.sh                       # ClearGlassInc/ClearGlassInc.github.io
#     scripts/fix_pages_source.sh owner/repo            # any repo
#
set -euo pipefail

REPO="${1:-ClearGlassInc/ClearGlassInc.github.io}"
API="https://api.github.com/repos/${REPO}/pages"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "::error::GITHUB_TOKEN is not set. Export an admin-scoped PAT first:" >&2
  echo "    export GITHUB_TOKEN=github_pat_xxx   # Pages: write + Administration" >&2
  exit 1
fi

auth=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
common=(-sS -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28")

echo "Repo:   ${REPO}"
echo "Reading current Pages configuration…"
current=$(curl "${common[@]}" "${auth[@]}" "${API}" || true)
echo "${current}"

build_type=$(printf '%s' "${current}" | grep -o '"build_type"[^,}]*' || true)
echo "Current ${build_type:-build_type: <unknown>}"

if printf '%s' "${build_type}" | grep -q '"workflow"'; then
  echo "✓ Pages source is already 'GitHub Actions' (build_type=workflow). Nothing to do."
  exit 0
fi

echo "Setting Pages build_type=workflow (Source -> 'GitHub Actions')…"
code=$(curl "${common[@]}" "${auth[@]}" -o /tmp/pages_fix.json -w '%{http_code}' \
  -X PUT "${API}" -d '{"build_type":"workflow"}' || true)
echo "PUT ${API} -> HTTP ${code}"
cat /tmp/pages_fix.json 2>/dev/null || true
echo

case "${code}" in
  200|204)
    echo "✓ Pages source set to GitHub Actions. The legacy 'pages build and"
    echo "  deployment' pipeline will no longer run, so production deployments"
    echo "  stop failing. Future publishes go solely through pages.yml."
    ;;
  403)
    echo "::error::HTTP 403 — token lacks admin scope. Use a fine-grained PAT" >&2
    echo "  with 'Pages' (write) AND 'Administration' (write) permissions, or" >&2
    echo "  flip Settings -> Pages -> Source to 'GitHub Actions' in the UI." >&2
    exit 1
    ;;
  *)
    echo "::error::Unexpected HTTP ${code}. See response body above." >&2
    exit 1
    ;;
esac
