#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ARTIFACT_DIR="${SHIELD_ARTIFACT_DIR:-artifacts/shield-g01}"
RUN_ID="${SHIELD_RUN_ID:-local-$(date -u +%Y%m%dT%H%M%SZ)}"
ROOT="/tmp/clearglass-shield-test"
mkdir -p "$ARTIFACT_DIR"
: > "$ARTIFACT_DIR/cycles.txt"

run_cycle(){
  local cycle="$1"
  "$SCRIPT_DIR/bootstrap-test-env.sh"
  ip netns exec cgshield-client python3 "$SCRIPT_DIR/probe.py" http
  ip netns exec cgshield-client python3 "$SCRIPT_DIR/probe.py" dns
  ip netns exec cgshield-client wg show > "$ARTIFACT_DIR/wg-client-$cycle.txt"
  ip netns exec cgshield-gateway wg show > "$ARTIFACT_DIR/wg-gateway-$cycle.txt"

  CLIENT_PUB="$(cat "$ROOT/client.pub")"

  # FI-03: revoked peer must lose protected access.
  ip netns exec cgshield-gateway wg set shield0 peer "$CLIENT_PUB" remove
  ip netns exec cgshield-client python3 "$SCRIPT_DIR/probe.py" blocked

  # Restore peer and verify recovery.
  ip netns exec cgshield-gateway wg set shield0 peer "$CLIENT_PUB" allowed-ips 10.77.0.2/32
  sleep 2
  ip netns exec cgshield-client python3 "$SCRIPT_DIR/probe.py" http

  # FI-06/LOCK: remove the client tunnel and require protected traffic to remain blocked.
  ip -n cgshield-client link del shield0
  ip netns exec cgshield-client python3 "$SCRIPT_DIR/probe.py" blocked

  printf '%s\n' "cycle=$cycle status=PASS" >> "$ARTIFACT_DIR/cycles.txt"
  "$SCRIPT_DIR/destroy-test-env.sh"
  "$SCRIPT_DIR/verify-clean.sh"
}

run_cycle 1
run_cycle 2
printf '%s\n' "run_id=$RUN_ID" "environment=isolated-disposable-test" "production_status=NOT_PRODUCTION" "commercial_status=BILLING_LOCKED" "stripe_interactions=0" "production_interactions=0" "customer_traffic=false" > "$ARTIFACT_DIR/run.txt"
