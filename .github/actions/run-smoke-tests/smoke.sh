#!/usr/bin/env bash
# Smoke-test a deployed URL: wait for it to come up, then assert each check.
#
#   SMOKE_BASE_URL   https://... (http only for localhost/127.0.0.1)
#   SMOKE_CHECKS     newline-separated "METHOD PATH EXPECTED[,EXPECTED...]"
#   SMOKE_ATTEMPTS   warm-up polls of the first check (default 30)
#   SMOKE_INTERVAL   seconds between warm-up polls (default 5)
#   SMOKE_TIMEOUT    per-request timeout in seconds (default 10)
#
# Exit 0 only when every check returned one of its expected statuses. Writes a
# table to $GITHUB_STEP_SUMMARY and passed=true|false to $GITHUB_OUTPUT when set.
set -euo pipefail

base="${SMOKE_BASE_URL:-}"
base="${base%/}"
checks="${SMOKE_CHECKS:-GET /health 200}"
attempts="${SMOKE_ATTEMPTS:-30}"
interval="${SMOKE_INTERVAL:-5}"
timeout="${SMOKE_TIMEOUT:-10}"

case "$base" in
  https://?*|http://127.0.0.1*|http://localhost*) ;;
  *)
    echo "::error title=Smoke test::refusing to test '$base': https:// required outside localhost"
    exit 2
    ;;
esac

probe() { # METHOD URL -> "STATUS SECONDS" (STATUS 000 on connection failure)
  curl --silent --output /dev/null --max-time "$timeout" --request "$1" \
    --write-out '%{http_code} %{time_total}' "$2" 2>/dev/null || echo "000 0"
}

matches() { # STATUS EXPECTED_CSV
  local IFS=','
  for want in $2; do [ "$1" = "$want" ] && return 0; done
  return 1
}

first="$(printf '%s\n' "$checks" | sed '/^[[:space:]]*$/d' | head -n1)"
read -r w_method w_path w_expect <<<"$first"
echo "Waiting for $base$w_path to answer $w_expect (up to $attempts x ${interval}s)"
ready=false
for i in $(seq 1 "$attempts"); do
  read -r status _ <<<"$(probe "$w_method" "$base$w_path")"
  if matches "$status" "$w_expect"; then ready=true; break; fi
  echo "  attempt $i/$attempts: $status"
  sleep "$interval"
done

failures=0
rows=""
while read -r method path expect; do
  [ -z "${method:-}" ] && continue
  result="FAIL"
  for try in 1 2 3; do
    read -r status secs <<<"$(probe "$method" "$base$path")"
    if matches "$status" "$expect"; then result="PASS"; break; fi
    if [ "$try" -lt 3 ]; then sleep 2; fi
  done
  if [ "$result" = "FAIL" ]; then failures=$((failures + 1)); fi
  echo "$result  $method $path -> $status (expected $expect, ${secs}s)"
  rows+="| $result | \`$method $path\` | $status | $expect | ${secs}s |"$'\n'
done <<<"$checks"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### Smoke tests: $base"
    echo
    if [ "$ready" != true ]; then echo "> Did not answer the warm-up check within $attempts attempts."; echo; fi
    echo "| Result | Check | Status | Expected | Time |"
    echo "|---|---|---|---|---|"
    printf '%s' "$rows"
  } >> "$GITHUB_STEP_SUMMARY"
fi

passed=true
if [ "$failures" -gt 0 ] || [ "$ready" != true ]; then passed=false; fi
if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "passed=$passed" >> "$GITHUB_OUTPUT"; fi

if [ "$passed" != true ]; then
  echo "::error title=Smoke test::$failures check(s) failed against $base"
  exit 1
fi
echo "All smoke checks passed against $base"
