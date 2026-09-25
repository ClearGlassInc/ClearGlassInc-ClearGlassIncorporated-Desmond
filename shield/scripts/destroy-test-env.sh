#!/usr/bin/env bash
set -euo pipefail
ip netns del cgshield-client 2>/dev/null || true
ip netns del cgshield-gateway 2>/dev/null || true
ip link del cg-veth-c 2>/dev/null || true
rm -rf /tmp/clearglass-shield-test
echo "Shield disposable environment destroyed"
