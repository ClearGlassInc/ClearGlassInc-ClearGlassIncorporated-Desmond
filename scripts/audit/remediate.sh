#!/usr/bin/env bash
# Safe, reviewable remediation for audit findings.
#
# This replaces the unsafe ad-hoc "auto-patch phase" that the org CI audit
# flagged, which (a) blind-committed unreviewed edits to every repo and
# (b) ran `sed -i` against a *directory* (e.g. .github/workflows), which errors
# out — corrupting the run instead of editing the intended file.
#
# Safety model (non-negotiable, mirrors the rest of this repo):
#   read -> show diff (review gate) -> human opt-in -> commit to a fix branch
#   -> open a PR. It NEVER:
#     * edits without first printing a unified diff,
#     * commits/pushes unless you explicitly pass APPLY=1 (and PUSH=1),
#     * pushes to a default branch (always a dedicated audit/remediate-* branch),
#     * loops blindly over "every repo" — it only touches the explicit entries
#       in the remediation manifest.
#
# It is driven by a MANIFEST of explicit, reviewed edits — not a wildcard sweep.
# Each line: <relative/path/to/file><TAB><sed-expression>
# Blank lines and lines starting with '#' are ignored.
#
# Usage:
#   scripts/audit/remediate.sh [manifest]            # DRY-RUN (default): diff only
#   APPLY=1 scripts/audit/remediate.sh [manifest]    # apply + commit to fix branch
#   APPLY=1 PUSH=1 scripts/audit/remediate.sh        # ...and push the fix branch
#
# Env:
#   MANIFEST   default ./scripts/audit/remediation.manifest
#   REPO_ROOT  default: git toplevel of CWD (edits are confined to it)
#   APPLY      1 = write changes + commit (default 0 = dry-run)
#   PUSH       1 = push the fix branch after committing (requires APPLY=1)
#   BRANCH     fix branch name (default audit/remediate-<UTC date>)
set -euo pipefail

MANIFEST="${1:-${MANIFEST:-./scripts/audit/remediation.manifest}}"
APPLY="${APPLY:-0}"
PUSH="${PUSH:-0}"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
BRANCH="${BRANCH:-audit/remediate-$(date -u +%Y%m%d)}"

log()  { echo "[remediate] $*" >&2; }
die()  { echo "[remediate] ERROR: $*" >&2; exit 1; }

[[ -f "$MANIFEST" ]] || die "manifest not found: $MANIFEST"
command -v sed >/dev/null || die "sed not installed"

if [[ "$PUSH" == "1" && "$APPLY" != "1" ]]; then
  die "PUSH=1 requires APPLY=1 (refusing to push without applying/committing)"
fi

# In APPLY mode, refuse up front if we're on the default branch — BEFORE writing
# any files — so a refusal never leaves uncommitted edits behind on main.
if [[ "$APPLY" == "1" ]] && git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  default_branch="$(git -C "$REPO_ROOT" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || echo main)"
  current_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
  if [[ "$current_branch" == "$default_branch" ]]; then
    die "refusing to apply on the default branch ($default_branch); checkout a fix branch first"
  fi
fi

log "manifest:  $MANIFEST"
log "repo root: $REPO_ROOT"
log "mode:      $([[ "$APPLY" == "1" ]] && echo APPLY || echo DRY-RUN)"

changed_files=()
planned=0
skipped=0

# ---- 1. Process each explicit manifest entry --------------------------------
while IFS=$'\t' read -r rel expr || [[ -n "${rel:-}" ]]; do
  # Skip blanks and comments.
  [[ -z "${rel// /}" ]] && continue
  [[ "${rel:0:1}" == "#" ]] && continue
  [[ -n "${expr:-}" ]] || die "manifest line for '$rel' has no <TAB>sed-expression"

  target="$REPO_ROOT/$rel"

  # --- The bug fix: never operate on a directory or a missing path. The old
  #     auto-patch ran `sed -i ... .github/workflows` (a directory) and errored.
  if [[ -d "$target" ]]; then
    log "SKIP  $rel — is a directory, not a file (this is exactly the old bug; "
    log "      point the manifest at a specific workflow file instead)"
    skipped=$((skipped + 1))
    continue
  fi
  if [[ ! -f "$target" ]]; then
    log "SKIP  $rel — file does not exist under repo root"
    skipped=$((skipped + 1))
    continue
  fi

  # --- Compute the edit on a temp copy so we can show a diff before touching
  #     the real file (review gate).
  tmp="$(mktemp)"
  if ! sed "$expr" "$target" > "$tmp" 2>/dev/null; then
    rm -f "$tmp"
    die "sed expression failed for $rel: '$expr'"
  fi

  if diff -q "$target" "$tmp" >/dev/null 2>&1; then
    log "no-op $rel — expression matched nothing; file unchanged"
    rm -f "$tmp"
    skipped=$((skipped + 1))
    continue
  fi

  echo "----- proposed change: $rel -----"
  diff -u "$target" "$tmp" || true
  echo "---------------------------------"
  planned=$((planned + 1))

  if [[ "$APPLY" == "1" ]]; then
    cp "$tmp" "$target"
    changed_files+=("$rel")
    log "applied $rel"
  fi
  rm -f "$tmp"
done < "$MANIFEST"

log "summary: $planned change(s) planned, $skipped entr(y/ies) skipped"

# ---- 2. Dry-run stops here (no writes, no commits, no pushes) ---------------
if [[ "$APPLY" != "1" ]]; then
  log "DRY-RUN complete. No files were modified. Re-run with APPLY=1 to commit"
  log "the changes above onto branch '$BRANCH' (review the diffs first)."
  exit 0
fi

if [[ "${#changed_files[@]}" -eq 0 ]]; then
  log "APPLY requested but nothing changed; not creating a commit."
  exit 0
fi

# ---- 3. Commit onto a dedicated fix branch (never the default branch) -------
# The default-branch guard already ran up front (before any writes).
cd "$REPO_ROOT"
git checkout -B "$BRANCH"
git add -- "${changed_files[@]}"
git commit -m "audit: apply reviewed remediation manifest ($planned file(s))"
log "committed ${#changed_files[@]} file(s) on $BRANCH"

if [[ "$PUSH" == "1" ]]; then
  git push -u origin "$BRANCH"
  log "pushed $BRANCH — open a PR for human review before merging."
else
  log "not pushing (PUSH!=1). Push with: git push -u origin $BRANCH, then open a PR."
fi
