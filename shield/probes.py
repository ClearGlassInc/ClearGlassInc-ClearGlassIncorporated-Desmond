"""Synthetic network probes. Every target is a test-only address in this topology."""

from __future__ import annotations

import json
import socket
import struct

RCODE_NXDOMAIN = 3


def dns_query(name: str, server: str, port: int, timeout: float = 2.0) -> tuple[int, str | None]:
    """Send one A query. Returns (rcode, first IPv4 answer or None). Raises OSError on no reply."""
    qid = 0x4731
    qname = b"".join(bytes([len(x)]) + x for x in name.encode().split(b".")) + b"\0"
    packet = struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0) + qname + struct.pack("!HH", 1, 1)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(packet, (server, port))
        data, _ = s.recvfrom(2048)
    if len(data) < 12 or data[:2] != struct.pack("!H", qid):
        raise OSError("malformed DNS reply")
    flags, _qd, ancount = struct.unpack("!HHH", data[2:8])
    rcode = flags & 0x000F
    if ancount and len(data) >= 4:
        return rcode, socket.inet_ntoa(data[-4:])
    return rcode, None


def http_get(host: str, port: int, path: str = "/", timeout: float = 2.0) -> tuple[int, bytes]:
    """Plain HTTP/1.0 GET. Returns (status, body). Raises OSError when unreachable."""
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(f"GET {path} HTTP/1.0\r\nHost: service.shield.test\r\n\r\n".encode())
        chunks = []
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks)
    head, _, body = raw.partition(b"\r\n\r\n")
    try:
        status = int(head.split(b" ", 2)[1])
    except (IndexError, ValueError) as exc:
        raise OSError("malformed HTTP reply") from exc
    return status, body


def tcp_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def underlay_state(host: str, port: int, timeout: float = 1.5) -> str:
    """'up' if the host answers at all (a refused TCP connect counts), else 'unreachable'."""
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return "up"
    except ConnectionRefusedError:
        return "up"
    except OSError:
        return "unreachable"


def main(argv: list[str]) -> int:
    """CLI used by the suite inside a namespace. Prints one JSON object."""
    mode = argv[0]
    host = argv[1]
    port = int(argv[2])
    out: dict[str, object] = {"mode": mode}
    if mode == "http":
        path = argv[3] if len(argv) > 3 else "/"
        try:
            status, body = http_get(host, port, path)
            out.update(reachable=True, status=status, marker=b"synthetic-service" in body)
            if path == "/health" and status == 200:
                out["health"] = json.loads(body)
        except OSError as exc:
            out.update(reachable=False, error_class=type(exc).__name__)
    elif mode == "tcp":
        out["reachable"] = tcp_reachable(host, port)
    elif mode == "dns":
        name = argv[3]
        try:
            rcode, answer = dns_query(name, host, port)
            out.update(answered=True, rcode=rcode, answer=answer)
        except OSError as exc:
            out.update(answered=False, error_class=type(exc).__name__)
    else:
        raise SystemExit(f"unknown probe mode {mode}")
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
