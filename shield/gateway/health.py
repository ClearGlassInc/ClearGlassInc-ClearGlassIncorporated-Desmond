"""Gateway health endpoint, bound to the gateway's tunnel address only.

Only GET /health answers. Every other path, including the usual debug and
metrics paths, is 404. The body carries state and counts, never keys, peer
configuration, addresses or traffic.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys

from shield.common import HEALTH_PORT, TUNNEL_GATEWAY, WG_GATEWAY, link_exists, peer_count

HEALTH_FIELDS = ("environment", "gateway_state", "peer_count", "test_mode", "production_status")


def health_body(iface: str = WG_GATEWAY) -> dict[str, object]:
    up = link_exists(iface)
    peers = peer_count(iface) if up else 0
    return {
        "environment": "isolated-disposable-test",
        "gateway_state": "healthy" if up else "degraded",
        "peer_count": peers,
        "test_mode": True,
        "production_status": "not_production",
    }


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(health_body()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else TUNNEL_GATEWAY
    port = int(sys.argv[2]) if len(sys.argv) > 2 else HEALTH_PORT
    HTTPServer((host, port), Health).serve_forever()
