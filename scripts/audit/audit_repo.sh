#!/usr/bin/env bash
# Audit a single GitHub repo and emit a JSON record.
#
# Usage: ./audit_repo.sh <owner/name>
#
# Writes: $OUT_DIR/<owner>_<name>.json
# Env:
#   OUT_DIR        default ./audit-out/repos
#   CLONE_DIR      default ./audit-out/clones (cleaned per repo unless KEEP_CLONES=1)
#   BOT_WINDOW     default 30 (days for bot-commit count)
#   SKIP_DEPS      set to 1 to skip pip-audit / npm audit (faster)
#   SKIP_CLONE     set to 1 to skip clone-based checks (deps only need clone)
#
# Requires: gh (auth'd), jq, git. Optional: pip-audit, npm (auto-skipped if missing).
set -euo pipefail

REPO="${1:?usage: audit_repo.sh <owner/name>}"
OUT_DIR="${OUT_DIR:-./audit-out/repos}"
CLONE_DIR="${CLONE_DIR:-./audit-out/clones}"
BOT_WINDOW="${BOT_WINDOW:-30}"

mkdir -p "$OUT_DIR" "$CLONE_DIR"

owner="${REPO%%/*}"
name="${REPO##*/}"
slug="${owner}_${name}"
out="$OUT_DIR/${slug}.json"

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
since="$(date -u -d "${BOT_WINDOW} days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
        || date -u -v-"${BOT_WINDOW}"d +%Y-%m-%dT%H:%M:%SZ)"

log() { echo "[audit:$REPO] $*" >&2; }

# ---- 1. Repo metadata + branch protection + secret scanning -----------------
log "metadata + protection"
meta_json="$(gh api "repos/$REPO" 2>/dev/null || echo '{}')"
default_branch="$(jq -r '.default_branch // "main"' <<<"$meta_json")"
visibility="$(jq -r '.visibility // "unknown"' <<<"$meta_json")"
archived="$(jq -r '.archived // false' <<<"$meta_json")"

secret_scanning="$(jq -r '.security_and_analysis.secret_scanning.status // "unknown"' <<<"$meta_json")"
secret_push_prot="$(jq -r '.security_and_analysis.secret_scanning_push_protection.status // "unknown"' <<<"$meta_json")"

prot_json="$(gh api "repos/$REPO/branches/$default_branch/protection" 2>/dev/null || echo '{}')"
required_reviews="$(jq -r '.required_pull_request_reviews.required_approving_review_count // 0' <<<"$prot_json")"
required_checks="$(jq -r '[.required_status_checks.contexts // []] | flatten | length' <<<"$prot_json")"
enforce_admins="$(jq -r '.enforce_admins.enabled // false' <<<"$prot_json")"

# ---- 2. Workflows: list + last run status ----------------------------------
log "workflows + runs"
workflows_json="$(gh api "repos/$REPO/actions/workflows" --paginate 2>/dev/null || echo '{"workflows":[]}')"
workflow_count="$(jq '.workflows | length' <<<"$workflows_json")"

# Per-workflow latest run conclusion
workflows_summary='[]'
if [[ "$workflow_count" -gt 0 ]]; then
  workflows_summary="$(jq -c '[.workflows[] | {id, name, path, state}]' <<<"$workflows_json")"
  enriched='[]'
  while IFS= read -r row; do
    wf_id="$(jq -r '.id' <<<"$row")"
    runs="$(gh api "repos/$REPO/actions/workflows/$wf_id/runs?per_page=1" 2>/dev/null || echo '{}')"
    last_conclusion="$(jq -r '.workflow_runs[0].conclusion // "none"' <<<"$runs")"
    last_status="$(jq -r '.workflow_runs[0].status // "none"' <<<"$runs")"
    last_at="$(jq -r '.workflow_runs[0].updated_at // ""' <<<"$runs")"
    row="$(jq -c \
      --arg c "$last_conclusion" --arg s "$last_status" --arg t "$last_at" \
      '. + {last_conclusion:$c, last_status:$s, last_run_at:$t}' <<<"$row")"
    enriched="$(jq -c --argjson r "$row" '. + [$r]' <<<"$enriched")"
  done < <(jq -c '.[]' <<<"$workflows_summary")
  workflows_summary="$enriched"
fi

# ---- 3. Bot health: commits + open PRs by login ----------------------------
log "bot health"
# Commits in window, grouped by author login
commits_json="$(gh api "repos/$REPO/commits?since=$since&per_page=100" --paginate 2>/dev/null || echo '[]')"
bot_commits="$(jq '[.[] | .author.login // .commit.author.name // "unknown"
                   | select(test("(?i)bot|dependabot|renovate|claude"))] | length' <<<"$commits_json")"
total_commits="$(jq 'length' <<<"$commits_json")"

# Open PRs by bot login
pr_json="$(gh api "repos/$REPO/pulls?state=open&per_page=100" --paginate 2>/dev/null || echo '[]')"
bot_open_prs="$(jq '[.[] | select(.user.login | test("(?i)bot|dependabot|renovate|claude"))] | length' <<<"$pr_json")"
total_open_prs="$(jq 'length' <<<"$pr_json")"

# ---- 4. Dependency audit (requires clone) ----------------------------------
pip_high=0; pip_critical=0; pip_status="skipped"
npm_high=0; npm_critical=0; npm_status="skipped"
clone_path=""

if [[ "${SKIP_CLONE:-0}" != "1" ]]; then
  clone_path="$CLONE_DIR/$slug"
  rm -rf "$clone_path"
  log "clone"
  if gh repo clone "$REPO" "$clone_path" -- --depth 1 --quiet 2>/dev/null; then
    if [[ "${SKIP_DEPS:-0}" != "1" ]]; then
      # pip-audit
      if command -v pip-audit >/dev/null 2>&1; then
        pip_targets=()
        [[ -f "$clone_path/requirements.txt" ]] && pip_targets+=(-r "$clone_path/requirements.txt")
        for f in "$clone_path"/requirements*.txt; do
          [[ -f "$f" && "$f" != "$clone_path/requirements.txt" ]] && pip_targets+=(-r "$f")
        done
        [[ -f "$clone_path/pyproject.toml" ]] && pip_targets+=(--project-path "$clone_path")
        if (( ${#pip_targets[@]} > 0 )); then
          log "pip-audit"
          pip_out="$(pip-audit --format json "${pip_targets[@]}" 2>/dev/null || echo '[]')"
          pip_high="$(jq '[.dependencies[]?.vulns[]? | select(.severity? // "" | ascii_downcase == "high")] | length' <<<"$pip_out" 2>/dev/null || echo 0)"
          pip_critical="$(jq '[.dependencies[]?.vulns[]? | select(.severity? // "" | ascii_downcase == "critical")] | length' <<<"$pip_out" 2>/dev/null || echo 0)"
          pip_status="ok"
        else
          pip_status="no-manifest"
        fi
      else
        pip_status="pip-audit-missing"
      fi

      # npm audit
      if [[ -f "$clone_path/package.json" ]] && command -v npm >/dev/null 2>&1; then
        log "npm audit"
        ( cd "$clone_path" && npm install --package-lock-only --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 || true )
        npm_out="$( ( cd "$clone_path" && npm audit --json 2>/dev/null ) || echo '{}')"
        npm_high="$(jq '.metadata.vulnerabilities.high // 0' <<<"$npm_out")"
        npm_critical="$(jq '.metadata.vulnerabilities.critical // 0' <<<"$npm_out")"
        npm_status="ok"
      elif [[ -f "$clone_path/package.json" ]]; then
        npm_status="npm-missing"
      else
        npm_status="no-manifest"
      fi
    fi
    [[ "${KEEP_CLONES:-0}" == "1" ]] || rm -rf "$clone_path"
  else
    log "clone failed"
    pip_status="clone-failed"; npm_status="clone-failed"
  fi
fi

# ---- 5. Emit record ---------------------------------------------------------
jq -n \
  --arg repo "$REPO" \
  --arg ts "$ts" \
  --arg visibility "$visibility" \
  --arg default_branch "$default_branch" \
  --argjson archived "$archived" \
  --arg secret_scanning "$secret_scanning" \
  --arg secret_push_prot "$secret_push_prot" \
  --argjson required_reviews "$required_reviews" \
  --argjson required_checks "$required_checks" \
  --argjson enforce_admins "$enforce_admins" \
  --argjson workflow_count "$workflow_count" \
  --argjson workflows "$workflows_summary" \
  --argjson bot_commits "$bot_commits" \
  --argjson total_commits "$total_commits" \
  --argjson bot_open_prs "$bot_open_prs" \
  --argjson total_open_prs "$total_open_prs" \
  --argjson bot_window "$BOT_WINDOW" \
  --arg pip_status "$pip_status" \
  --argjson pip_high "$pip_high" \
  --argjson pip_critical "$pip_critical" \
  --arg npm_status "$npm_status" \
  --argjson npm_high "$npm_high" \
  --argjson npm_critical "$npm_critical" \
  '{
    repo: $repo, audited_at: $ts,
    meta: {visibility:$visibility, default_branch:$default_branch, archived:$archived},
    security: {
      secret_scanning:$secret_scanning,
      secret_scanning_push_protection:$secret_push_prot,
      branch_protection: {
        required_reviews:$required_reviews,
        required_checks:$required_checks,
        enforce_admins:$enforce_admins
      }
    },
    workflows: {count:$workflow_count, items:$workflows},
    bot_health: {
      window_days:$bot_window,
      bot_commits:$bot_commits, total_commits:$total_commits,
      bot_open_prs:$bot_open_prs, total_open_prs:$total_open_prs
    },
    deps: {
      pip: {status:$pip_status, high:$pip_high, critical:$pip_critical},
      npm: {status:$npm_status, high:$npm_high, critical:$npm_critical}
    }
  }' > "$out"

log "wrote $out"
