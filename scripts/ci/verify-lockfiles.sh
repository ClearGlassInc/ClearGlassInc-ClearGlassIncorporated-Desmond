#!/usr/bin/env sh
set -eu
# verify-lockfiles.sh — pass if a supported dependency lockfile is present,
# fail closed otherwise. A missing lockfile means non-reproducible installs.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

for f in package-lock.json pnpm-lock.yaml yarn.lock; do
  if [ -f "$ROOT/$f" ]; then
    echo "verify-lockfiles: found $f"
    exit 0
  fi
done

echo "verify-lockfiles: FAIL: no lockfile found (package-lock.json / pnpm-lock.yaml / yarn.lock)" >&2
exit 1
