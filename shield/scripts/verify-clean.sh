#!/usr/bin/env bash
set -euo pipefail
if ip netns list | grep -Eq '(^|[[:space:]])cgshield-(client|gateway)([[:space:]]|$)'; then
  echo "Shield test namespaces remain" >&2
  exit 1
fi
if ip link show 2>/dev/null | grep -Eq 'cg-veth-[cg]'; then
  echo "Shield test veth remains" >&2
  exit 1
fi
[ ! -e /tmp/clearglass-shield-test ] || { echo "Shield temp state remains" >&2; exit 1; }
echo "Shield test environment clean"
