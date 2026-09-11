#!/usr/bin/env bash
# Single source of truth for the Cloudflare Pages build.
#
# Produces the deployable static bundle from the repository using the site's own
# fail-closed publisher, tools/build_pages.py. Use this for both paths in
# README.md: as the Pages "build command", or locally before a direct upload.
#
#   deployment/cloudflare-pages/build.sh            # -> ./dist
#   OUT=/tmp/site deployment/cloudflare-pages/build.sh
#
# stdlib-only: no pip install, so it runs anywhere Python 3 exists.
set -euo pipefail

OUT="${OUT:-dist}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

python3 tools/build_pages.py "$OUT"

# Fail closed rather than publish a bundle missing its own guarantees. Each of
# these has been a real defect in this repository at least once.
for required in index.html 404.html _headers _redirects .well-known/security.txt; do
  if [ ! -e "$OUT/$required" ]; then
    echo "build.sh: refusing to publish — $required missing from $OUT" >&2
    exit 1
  fi
done

# Source and internal trees must not be reachable over HTTP.
for denied in bots tests scripts sentinel tools percival_v9 customer-profiles operations workflows; do
  if [ -e "$OUT/$denied" ]; then
    echo "build.sh: refusing to publish — $denied leaked into $OUT" >&2
    exit 1
  fi
done

echo "build.sh: $(find "$OUT" -type f | wc -l) files in $OUT"
