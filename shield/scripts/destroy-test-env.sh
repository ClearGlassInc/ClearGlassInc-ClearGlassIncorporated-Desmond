#!/usr/bin/env bash
set -euo pipefail
ROOT="/tmp/clearglass-shield-test"
for pidfile in "$ROOT"/*.pid; do
  [ -f "$pidfile" ] || continue
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
done
ip netns del cgshield-client 2>/dev/null || true
ip netns del cgshield-gateway 2>/dev/null || true
ip link del cg-veth-c 2>/dev/null || true
rm -rf "$ROOT"
