#!/usr/bin/env bash
set -euo pipefail

command -v ip >/dev/null || { echo "iproute2 required" >&2; exit 2; }
command -v wg >/dev/null || { echo "wireguard-tools required" >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 2; }
command -v iptables >/dev/null || { echo "iptables required" >&2; exit 2; }

ROOT="/tmp/clearglass-shield-test"
CLIENT_NS="cgshield-client"
GW_NS="cgshield-gateway"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

bash "$SCRIPT_DIR/destroy-test-env.sh" >/dev/null 2>&1 || true
rm -rf "$ROOT"
mkdir -p "$ROOT"
chmod 700 "$ROOT"
umask 077

ip netns add "$CLIENT_NS"
ip netns add "$GW_NS"
ip link add cg-veth-c type veth peer name cg-veth-g
ip link set cg-veth-c netns "$CLIENT_NS"
ip link set cg-veth-g netns "$GW_NS"

ip -n "$CLIENT_NS" addr add 192.0.2.2/30 dev cg-veth-c
ip -n "$GW_NS" addr add 192.0.2.1/30 dev cg-veth-g
ip -n "$CLIENT_NS" link set lo up
ip -n "$GW_NS" link set lo up
ip -n "$CLIENT_NS" link set cg-veth-c up
ip -n "$GW_NS" link set cg-veth-g up

CLIENT_PRIV="$(wg genkey)"
CLIENT_PUB="$(printf '%s' "$CLIENT_PRIV" | wg pubkey)"
GW_PRIV="$(wg genkey)"
GW_PUB="$(printf '%s' "$GW_PRIV" | wg pubkey)"

printf '%s\n' "$CLIENT_PRIV" > "$ROOT/client.key"
printf '%s\n' "$GW_PRIV" > "$ROOT/gateway.key"
printf '%s\n' "$CLIENT_PUB" > "$ROOT/client.pub"
printf '%s\n' "$GW_PUB" > "$ROOT/gateway.pub"
chmod 600 "$ROOT"/*.key "$ROOT"/*.pub

ip -n "$GW_NS" link add shield0 type wireguard
ip -n "$GW_NS" addr add 10.77.0.1/24 dev shield0
printf '%s' "$GW_PRIV" | ip netns exec "$GW_NS" wg set shield0 private-key /dev/stdin listen-port 51820
ip -n "$GW_NS" link set shield0 up

ip -n "$CLIENT_NS" link add shield0 type wireguard
ip -n "$CLIENT_NS" addr add 10.77.0.2/24 dev shield0
printf '%s' "$CLIENT_PRIV" | ip netns exec "$CLIENT_NS" wg set shield0 private-key /dev/stdin peer "$GW_PUB" allowed-ips 10.77.0.0/24 endpoint 192.0.2.1:51820 persistent-keepalive 1
ip -n "$CLIENT_NS" link set shield0 up
ip -n "$CLIENT_NS" route replace 10.77.0.0/24 dev shield0
ip netns exec "$GW_NS" wg set shield0 peer "$CLIENT_PUB" allowed-ips 10.77.0.2/32

ip netns exec "$CLIENT_NS" iptables -A OUTPUT -d 10.77.0.0/24 -o shield0 -j ACCEPT
ip netns exec "$CLIENT_NS" iptables -A OUTPUT -d 10.77.0.0/24 -j REJECT

nohup ip netns exec "$GW_NS" python3 -m http.server 8080 --bind 10.77.0.1 >"$ROOT/http.log" 2>&1 &
echo $! > "$ROOT/http.pid"
nohup ip netns exec "$GW_NS" python3 "$SCRIPT_DIR/dns_server.py" >"$ROOT/dns.log" 2>&1 &
echo $! > "$ROOT/dns.pid"
nohup ip netns exec "$GW_NS" python3 -c 'from http.server import BaseHTTPRequestHandler,HTTPServer; H=type("H",(BaseHTTPRequestHandler,),{"do_GET":lambda s:(s.send_response(200),s.end_headers(),s.wfile.write(b"healthy")),"log_message":lambda *a:None}); HTTPServer(("10.77.0.1",18080),H).serve_forever()' >"$ROOT/health.log" 2>&1 &
echo $! > "$ROOT/health.pid"

cat > "$ROOT/config.json" <<'JSON'
{"environment":"isolated-disposable-test","gateway_endpoint":"192.0.2.1:51820","gateway_identity":"TEST_EPHEMERAL","public_key":"TEST_EPHEMERAL","tunnel_address":"10.77.0.2/24","dns_policy":"test-only","network_lock":true,"configuration_version":"1"}
JSON

printf '%s\n' "environment=isolated-disposable-test" "client_public_fingerprint=$(printf '%s' "$CLIENT_PUB" | sha256sum | cut -d' ' -f1)" "gateway_public_fingerprint=$(printf '%s' "$GW_PUB" | sha256sum | cut -d' ' -f1)" > "$ROOT/safe-identities.txt"
echo "Shield disposable environment created"
