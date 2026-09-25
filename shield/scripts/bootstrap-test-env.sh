#!/usr/bin/env bash
set -euo pipefail
command -v ip >/dev/null || { echo "iproute2 required" >&2; exit 2; }
command -v wg >/dev/null || { echo "wireguard-tools required" >&2; exit 2; }
ROOT="/tmp/clearglass-shield-test"
ip netns add cgshield-client
ip netns add cgshield-gateway
ip link add cg-veth-c type veth peer name cg-veth-g
ip link set cg-veth-c netns cgshield-client
ip link set cg-veth-g netns cgshield-gateway
ip -n cgshield-client addr add 192.0.2.2/30 dev cg-veth-c
ip -n cgshield-gateway addr add 192.0.2.1/30 dev cg-veth-g
ip -n cgshield-client link set lo up
ip -n cgshield-gateway link set lo up
ip -n cgshield-client link set cg-veth-c up
ip -n cgshield-gateway link set cg-veth-g up
mkdir -p "$ROOT"; chmod 700 "$ROOT"
umask 077
CLIENT_PRIV="$(wg genkey)"; CLIENT_PUB="$(printf '%s' "$CLIENT_PRIV"|wg pubkey)"
GW_PRIV="$(wg genkey)"; GW_PUB="$(printf '%s' "$GW_PRIV"|wg pubkey)"
printf '%s
' "$CLIENT_PRIV" > "$ROOT/client.key"
printf '%s
' "$GW_PRIV" > "$ROOT/gateway.key"
printf '%s
' "$CLIENT_PUB" > "$ROOT/client.pub"
printf '%s
' "$GW_PUB" > "$ROOT/gateway.pub"
ip -n cgshield-gateway link add shield0 type wireguard
ip -n cgshield-gateway addr add 10.77.0.1/24 dev shield0
printf '%s' "$GW_PRIV" | ip netns exec cgshield-gateway wg set shield0 private-key /dev/stdin listen-port 51820 peer "$CLIENT_PUB" allowed-ips 10.77.0.2/32
ip -n cgshield-gateway link set shield0 up
ip -n cgshield-client link add shield0 type wireguard
ip -n cgshield-client addr add 10.77.0.2/24 dev shield0
printf '%s' "$CLIENT_PRIV" | ip netns exec cgshield-client wg set shield0 private-key /dev/stdin peer "$GW_PUB" allowed-ips 10.77.0.0/24 endpoint 192.0.2.1:51820 persistent-keepalive 5
ip -n cgshield-client link set shield0 up
ip -n cgshield-client route replace 10.77.0.0/24 dev shield0
printf '%s
' '{"environment":"isolated-disposable-test","gateway_endpoint":"192.0.2.1:51820","gateway_identity":"TEST_EPHEMERAL","public_key":"TEST_EPHEMERAL","tunnel_address":"10.77.0.2/24","dns_policy":"test-only","network_lock":true,"configuration_version":"1"}' > "$ROOT/config.json"
echo "Shield disposable environment created"
