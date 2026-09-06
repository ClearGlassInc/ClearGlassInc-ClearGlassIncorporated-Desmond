#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/ClearGlassInc/ClearGlassInc.github.io.git"
BRANCH="main"
COMMIT_MSG="${1:-Deploy Guardian legal review bot}"

echo "==> Checking repository..."
if [ ! -d ".git" ]; then
  echo "No .git folder found. Initializing repo..."
  git init
  git remote add origin "$REPO_URL"
fi

echo "==> Syncing latest main..."
git fetch origin "$BRANCH"
git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH"
git pull --rebase origin "$BRANCH"

echo "==> Staging changes..."
git add .

echo "==> Checking staged diff..."
if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

echo "==> Committing..."
git commit -m "$COMMIT_MSG"

echo "==> Pushing to GitHub..."
git push origin "$BRANCH"

echo "==> Push complete."
