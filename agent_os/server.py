# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""HTTP front end for the head agent: submit, watch, cancel, approve.

Stdlib ``http.server`` with in-process worker threads, for a single operator
host next to a repository checkout. It is not the commerce control plane and
does not ship in that image: the head agent runs repository commands, so it
lives where the repository is.

Routes::

    GET  /                                console (static; holds no data)
    GET  /healthz                         liveness only — the process answers
    GET  /readyz                          store reachable, registry valid, workers alive
    GET  /api/agents                      the worker registry and its contracts
    GET  /api/missions                    recent missions
    POST /api/missions                    {"objective", "idempotency_key"?}
    GET  /api/missions/{id}               mission, tasks, outputs, evidence
    GET  /api/missions/{id}/events        hash-chained event log + verification
    POST /api/missions/{id}/cancel
    POST /api/tasks/{id}/decision         {"decision": "approve"|"reject", "reason", "approver"?}
    GET  /api/metrics                     task outcomes, queue depth, retries, data freshness

Authentication fails closed. ``AGENT_OS_API_TOKEN`` (at least 24 characters)
is required to start, and every ``/api`` route needs it as a bearer token.
Decisions need a *different* token, ``AGENT_OS_APPROVER_TOKEN``: whoever can
submit work cannot approve it with the same credential. With no approver token
set, gated tasks wait and every decision is refused.

    AGENT_OS_API_TOKEN=... AGENT_OS_APPROVER_TOKEN=... python -m agent_os.server

Bind defaults to 127.0.0.1. Exposing it further needs TLS in front of it.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import re
import signal
import sys
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .head import DEFAULT_DB, HeadAgent
from .redaction import redact
from .tasks import DelegationError, InvalidTransition, TaskStore

STATIC = Path(__file__).resolve().parent / "console"
MAX_BODY = 16_384
MIN_TOKEN = 24
MAX_OPEN_TASKS = 200
SUBMITS_PER_MINUTE = 30
_KEY = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_NAME = re.compile(r"^[A-Za-z0-9 ._@-]{1,64}$")
_ID = r"[a-z]{3}-[0-9a-f]{16}"

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; "
                               "connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; "
                               "frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "X-Frame-Options": "DENY",
}

log = logging.getLogger("agent_os.server")


class ConfigError(ValueError):
    """The server refuses to start rather than run open."""


@dataclass(frozen=True)
class Config:
    api_token: str
    approver_token: str | None
    db: str
    bind: str = "127.0.0.1"
    port: int = 8765
    workers: int = 1
    shutdown_grace: float = 30.0

    @classmethod
    def from_env(cls, env: dict[str, str] | os._Environ[str] | None = None) -> Config:
        source = os.environ if env is None else env
        api = source.get("AGENT_OS_API_TOKEN", "").strip()
        approver = source.get("AGENT_OS_APPROVER_TOKEN", "").strip() or None
        if len(api) < MIN_TOKEN:
            raise ConfigError(f"AGENT_OS_API_TOKEN must be set to at least {MIN_TOKEN} characters")
        if approver is not None:
            if len(approver) < MIN_TOKEN:
                raise ConfigError(f"AGENT_OS_APPROVER_TOKEN must be at least {MIN_TOKEN} characters")
            if hmac.compare_digest(api, approver):
                raise ConfigError("AGENT_OS_APPROVER_TOKEN must differ from AGENT_OS_API_TOKEN")
        try:
            port = int(source.get("AGENT_OS_PORT", "8765"))
            workers = int(source.get("AGENT_OS_WORKERS", "1"))
            grace = float(source.get("AGENT_OS_SHUTDOWN_GRACE", "30"))
        except ValueError as exc:
            raise ConfigError(f"invalid numeric setting: {exc}") from exc
        if not 1 <= workers <= 4:
            raise ConfigError("AGENT_OS_WORKERS must be between 1 and 4")
        return cls(api_token=api, approver_token=approver,
                   db=source.get("AGENT_OS_DB", "").strip() or str(DEFAULT_DB),
                   bind=source.get("AGENT_OS_BIND", "127.0.0.1").strip() or "127.0.0.1",
                   port=port, workers=workers, shutdown_grace=grace)


class _Throttle:
    """Per-client sliding window for submits; bounds what one caller can queue."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self.hits: dict[str, list[float]] = {}
        self.lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self.lock:
            recent = [t for t in self.hits.get(client, []) if now - t < 60]
            allowed = len(recent) < self.per_minute
            if allowed:
                recent.append(now)
            self.hits[client] = recent
            return allowed


class AgentServer:
    def __init__(self, config: Config, *, head: HeadAgent | None = None) -> None:
        self.config = config
        secrets = tuple(t for t in (config.api_token, config.approver_token) if t)
        self.head = head or HeadAgent(TaskStore(config.db), secrets=secrets,
                                      global_concurrency=config.workers)
        self.head.secrets = tuple(dict.fromkeys(self.head.secrets + secrets))
        self.stop = threading.Event()
        self.throttle = _Throttle(SUBMITS_PER_MINUTE)
        self.heartbeats: dict[str, float] = {}
        self.threads: list[threading.Thread] = []
        self.httpd = ThreadingHTTPServer((config.bind, config.port), self._handler())
        self.httpd.daemon_threads = True

    @property
    def address(self) -> tuple[str, int]:
        host, port = self.httpd.server_address[:2]
        return str(host), int(port)

    # ------------------------------------------------------------------ lifecycle
    def start_workers(self) -> None:
        for n in range(self.config.workers):
            worker_id = f"srv-{os.getpid()}-{n}"

            def beat(worker_id: str = worker_id) -> None:
                self.heartbeats[worker_id] = time.monotonic()

            thread = threading.Thread(target=self.head.work, args=(worker_id, self.stop),
                                      kwargs={"heartbeat": beat}, name=worker_id, daemon=True)
            thread.start()
            self.threads.append(thread)

    def serve_forever(self) -> None:
        self.start_workers()
        log.info(json.dumps({"event": "server_started", "bind": self.address[0], "port": self.address[1],
                             "workers": self.config.workers,
                             "approvals": self.config.approver_token is not None}))
        self.httpd.serve_forever(poll_interval=0.5)

    def shutdown(self) -> None:
        """Stop taking requests, let running tasks finish within the grace period."""
        log.info(json.dumps({"event": "shutdown_started", "grace_seconds": self.config.shutdown_grace}))
        self.head.begin_shutdown(self.config.shutdown_grace)
        self.stop.set()
        self.httpd.shutdown()
        for thread in self.threads:
            thread.join(timeout=self.config.shutdown_grace + 10)
        self.httpd.server_close()
        log.info(json.dumps({"event": "shutdown_complete"}))

    def readiness(self) -> tuple[bool, dict[str, Any]]:
        try:
            store_ok = self.head.store.ping()
        except Exception:  # noqa: BLE001 - any store error is "not ready"
            store_ok = False
        now = time.monotonic()
        alive = [w for w, t in self.heartbeats.items() if now - t < 15]
        checks = {"store": store_ok, "registry": True,
                  "workers_alive": len(alive), "workers_expected": self.config.workers,
                  "approvals_configured": self.config.approver_token is not None}
        return store_ok and len(alive) >= 1, checks

    # ------------------------------------------------------------------ HTTP
    def _handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "agent-os"
            sys_version = ""

            def log_message(self, fmt: str, *args: Any) -> None:  # route through JSON logging
                return

            # ---- responses
            def _send(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                for name, value in SECURITY_HEADERS.items():
                    self.send_header(name, value)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                if status == HTTPStatus.UNAUTHORIZED:
                    self.send_header("WWW-Authenticate", 'Bearer realm="agent-os"')
                self.end_headers()
                self.wfile.write(body)
                self._status = status

            def _json(self, status: int, payload: Any) -> None:
                text = redact(json.dumps(payload, default=str), literals=server.head.secrets)
                self._send(status, text.encode("utf-8"), "application/json; charset=utf-8")

            def _error(self, status: int, message: str) -> None:
                self._json(status, {"error": message})

            # ---- auth and input
            def _bearer(self) -> str:
                header = self.headers.get("Authorization", "")
                return header[7:].strip() if header[:7].lower() == "bearer " else ""

            def _authorised(self, *, approver: bool = False) -> bool:
                presented = self._bearer()
                expected = server.config.approver_token if approver else server.config.api_token
                if not presented:
                    self._error(HTTPStatus.UNAUTHORIZED, "bearer token required")
                    return False
                if expected is None:
                    self._error(HTTPStatus.FORBIDDEN, "approvals are not configured on this server")
                    return False
                if not hmac.compare_digest(presented.encode(), expected.encode()):
                    other = server.config.api_token if approver else server.config.approver_token
                    known = other is not None and hmac.compare_digest(presented.encode(), other.encode())
                    self._error(HTTPStatus.FORBIDDEN if known else HTTPStatus.UNAUTHORIZED,
                                "this token cannot do that" if known else "invalid token")
                    return False
                return True

            def _body(self) -> dict[str, Any] | None:
                if "application/json" not in self.headers.get("Content-Type", ""):
                    self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "send application/json")
                    return None
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = -1
                if not 0 <= length <= MAX_BODY:
                    self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"body must be at most {MAX_BODY} bytes")
                    return None
                try:
                    data = json.loads(self.rfile.read(length) or b"{}")
                except ValueError:
                    self._error(HTTPStatus.BAD_REQUEST, "body is not valid JSON")
                    return None
                if not isinstance(data, dict):
                    self._error(HTTPStatus.BAD_REQUEST, "body must be a JSON object")
                    return None
                return data

            def _static(self, name: str, content_type: str) -> None:
                self._send(HTTPStatus.OK, (STATIC / name).read_bytes(), content_type)

            # ---- dispatch
            def do_GET(self) -> None:  # noqa: N802 - http.server API
                self._dispatch("GET")

            def do_POST(self) -> None:  # noqa: N802 - http.server API
                self._dispatch("POST")

            def _dispatch(self, method: str) -> None:
                started = time.monotonic()
                self._status = 0
                url = urlparse(self.path)
                try:
                    self._route(method, url.path, parse_qs(url.query))
                except KeyError:
                    self._error(HTTPStatus.NOT_FOUND, "not found")
                except InvalidTransition as exc:
                    self._error(HTTPStatus.CONFLICT, str(exc))
                except (ValueError, DelegationError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                except Exception:  # noqa: BLE001 - never leak a traceback to the client
                    log.exception("request failed")
                    self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal error")
                log.info(json.dumps({"event": "http", "method": method, "path": url.path,
                                     "status": self._status,
                                     "ms": int((time.monotonic() - started) * 1000)}))

            def _route(self, method: str, path: str, query: dict[str, list[str]]) -> None:
                if method == "GET" and path in ("/", "/index.html"):
                    # Stored as .tmpl, not .html: GitHub Pages publishes this repository's
                    # root, and an ops console must not become a page on the public site.
                    return self._static("console.tmpl", "text/html; charset=utf-8")
                if method == "GET" and path in ("/console.js", "/console.css"):
                    kind = "text/javascript" if path.endswith(".js") else "text/css"
                    return self._static(path[1:], f"{kind}; charset=utf-8")
                if method == "GET" and path == "/healthz":
                    return self._json(HTTPStatus.OK, {"status": "alive"})
                if method == "GET" and path == "/readyz":
                    ready, checks = server.readiness()
                    return self._json(HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE,
                                      {"ready": ready, "checks": checks})
                if not path.startswith("/api/"):
                    raise KeyError(path)

                decision = re.fullmatch(rf"/api/tasks/({_ID})/decision", path)
                if method == "POST" and decision:
                    if not self._authorised(approver=True):
                        return None
                    return self._decide(decision.group(1))
                if not self._authorised():
                    return None

                if method == "GET" and path == "/api/agents":
                    return self._json(HTTPStatus.OK, {"agents": server.head.registry()})
                if method == "GET" and path == "/api/metrics":
                    return self._json(HTTPStatus.OK, server.head.metrics())
                if path == "/api/missions":
                    if method == "GET":
                        limit = int((query.get("limit") or ["20"])[0])
                        return self._json(HTTPStatus.OK, {"missions": server.head.store.list_missions(limit)})
                    if method == "POST":
                        return self._submit()
                mission = re.fullmatch(rf"/api/missions/({_ID})(/events|/cancel)?", path)
                if mission:
                    cid, tail = mission.group(1), mission.group(2)
                    if method == "GET" and tail is None:
                        found = server.head.store.get_mission(cid)
                        if found is None:
                            raise KeyError(cid)
                        return self._json(HTTPStatus.OK, found)
                    if method == "GET" and tail == "/events":
                        if server.head.store.get_mission(cid) is None:
                            raise KeyError(cid)
                        return self._json(HTTPStatus.OK, server.head.store.events(cid))
                    if method == "POST" and tail == "/cancel":
                        return self._json(HTTPStatus.OK, server.head.cancel(cid, by="api-operator"))
                if method not in ("GET", "POST"):
                    return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
                raise KeyError(path)

            def _submit(self) -> None:
                body = self._body()
                if body is None:
                    return
                if set(body) - {"objective", "idempotency_key"}:
                    return self._error(HTTPStatus.BAD_REQUEST, "unexpected fields")
                key = body.get("idempotency_key")
                if key is not None and (not isinstance(key, str) or not _KEY.match(key)):
                    return self._error(HTTPStatus.BAD_REQUEST, "idempotency_key must match [A-Za-z0-9._:-]{1,128}")
                if not server.throttle.allow(self.client_address[0]):
                    return self._error(HTTPStatus.TOO_MANY_REQUESTS, "too many submissions; retry in a minute")
                metrics = server.head.store.metrics()
                open_tasks = sum(metrics["tasks_by_status"].get(s, 0)
                                 for s in ("queued", "running", "waiting_for_approval"))
                if open_tasks >= MAX_OPEN_TASKS:
                    return self._error(HTTPStatus.TOO_MANY_REQUESTS, "task queue is full")
                mission = server.head.plan(body.get("objective"), requested_by="api-operator",
                                           idempotency_key=key)
                return self._json(HTTPStatus.CREATED if mission["created"] else HTTPStatus.OK, mission)

            def _decide(self, task_id: str) -> None:
                body = self._body()
                if body is None:
                    return
                decision, reason = body.get("decision"), body.get("reason")
                approver = body.get("approver") or "api-approver"
                if decision not in ("approve", "reject"):
                    return self._error(HTTPStatus.BAD_REQUEST, "decision must be approve or reject")
                if not isinstance(reason, str) or not 3 <= len(reason.strip()) <= 500:
                    return self._error(HTTPStatus.BAD_REQUEST, "a reason of 3-500 characters is required")
                if not isinstance(approver, str) or not _NAME.match(approver):
                    return self._error(HTTPStatus.BAD_REQUEST, "approver must be a short plain name")
                task = server.head.decide(task_id, approver=approver, approve=decision == "approve",
                                          reason=reason.strip())
                return self._json(HTTPStatus.OK, task)

        return Handler


class _JsonFormatter(logging.Formatter):
    def __init__(self, secrets: tuple[str, ...]) -> None:
        super().__init__()
        self.secrets = secrets

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        try:
            fields = json.loads(message)
            if not isinstance(fields, dict):
                raise ValueError
        except ValueError:
            fields = {"message": message}
        if record.exc_info:
            fields["exception"] = self.formatException(record.exc_info)
        line = json.dumps({"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
                           "level": record.levelname.lower(), "logger": record.name, **fields},
                          default=str)
        return redact(line, literals=self.secrets)


def main() -> int:
    try:
        config = Config.from_env()
    except ConfigError as exc:
        print(f"agent_os.server: {exc}", file=sys.stderr)
        return 2
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter(tuple(t for t in (config.api_token, config.approver_token) if t)))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    server = AgentServer(config)

    def on_signal(signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, name="shutdown", daemon=True).start()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    server.serve_forever()
    for thread in threading.enumerate():
        if thread.name == "shutdown":
            thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
