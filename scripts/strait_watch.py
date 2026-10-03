#!/usr/bin/env python3
"""Controlled, public-source change monitor for ClearGlass Strait Watch.

The MVP is stdlib-only and fails closed:
- HTTPS is required.
- Hosts must be explicitly allowlisted in the source registry.
- Only configured text content-types are processed.
- State is persisted locally as JSON.
- Changes are SHA-256 fingerprinted after normalization.
- Webhook alerts require an HMAC secret.
- No proxy rotation, credential scraping, or rate-limit evasion is implemented.

This tool does not connect to OT, production systems, payment systems, or customer data.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import json
import os
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT = 20
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
USER_AGENT = "ClearGlass-StraitWatch/1.0 (+public-source-monitoring)"

SUPPORTED_TEXT_TYPES = {
    "text/html",
    "text/plain",
    "application/json",
    "application/xml",
    "text/xml",
}


class ValidationError(ValueError):
    """Raised when a registry or source violates monitoring policy."""


class VisibleTextParser(HTMLParser):
    """Extract normalized visible text while ignoring scripts/styles."""

    _SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


@dataclass(frozen=True)
class Source:
    source_id: str
    authority: str
    url: str
    allowed_hosts: tuple[str, ...]
    content_types: tuple[str, ...]


def _content_type(raw: str | None) -> str:
    return (raw or "").split(";", 1)[0].strip().lower()


def normalize_content(content: bytes, content_type: str, charset: str | None = None) -> str:
    """Normalize supported content into a stable comparison representation."""
    encoding = charset or "utf-8"
    text = content.decode(encoding, errors="replace")

    if content_type == "application/json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"invalid JSON payload: {exc}") from exc
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    if content_type == "text/html":
        parser = VisibleTextParser()
        parser.feed(text)
        parser.close()
        text = " ".join(parser.parts)
        return " ".join(html.unescape(text).split())

    return " ".join(text.split())


def fingerprint(normalized_content: str) -> str:
    """Return the SHA-256 fingerprint used for change detection."""
    return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()


def load_registry(path: Path) -> tuple[dict[str, Any], list[Source]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot load source registry {path}: {exc}") from exc

    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        raise ValidationError("registry must contain a 'sources' array")

    default_timeout = int(raw.get("default_timeout_seconds", DEFAULT_TIMEOUT))
    max_response_bytes = int(raw.get("max_response_bytes", DEFAULT_MAX_BYTES))
    if default_timeout <= 0:
        raise ValidationError("default_timeout_seconds must be > 0")
    if max_response_bytes <= 0:
        raise ValidationError("max_response_bytes must be > 0")

    sources: list[Source] = []
    seen: set[str] = set()
    for item in raw["sources"]:
        if not isinstance(item, dict):
            raise ValidationError("each source entry must be an object")

        source_id = str(item.get("id", "")).strip()
        authority = str(item.get("authority", "")).strip()
        url = str(item.get("url", "")).strip()
        allowed_hosts = tuple(str(x).strip().lower() for x in item.get("allowed_hosts", []))
        content_types = tuple(str(x).strip().lower() for x in item.get("content_types", []))

        if not source_id or source_id in seen:
            raise ValidationError(f"duplicate or missing source id: {source_id!r}")
        seen.add(source_id)

        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValidationError(f"{source_id}: URL must use HTTPS and include a host")
        if parsed.username or parsed.password:
            raise ValidationError(f"{source_id}: embedded credentials are prohibited")
        if parsed.hostname.lower() not in allowed_hosts:
            raise ValidationError(f"{source_id}: URL host is not allowlisted")
        if not content_types or not set(content_types).issubset(SUPPORTED_TEXT_TYPES):
            raise ValidationError(
                f"{source_id}: content_types must be a non-empty subset of {sorted(SUPPORTED_TEXT_TYPES)}"
            )

        sources.append(
            Source(
                source_id=source_id,
                authority=authority,
                url=url,
                allowed_hosts=allowed_hosts,
                content_types=content_types,
            )
        )

    return {
        "version": str(raw.get("version", "1.0")),
        "default_timeout_seconds": default_timeout,
        "max_response_bytes": max_response_bytes,
    }, sources


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "sources": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot load state {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("sources", {}), dict):
        raise ValidationError("state must be an object with a 'sources' object")
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def fetch_source(source: Source, timeout: int, max_response_bytes: int) -> tuple[str, int, str]:
    """Fetch one explicitly allowlisted public source and return normalized text."""
    request = Request(
        source.url,
        headers={
            "Accept": "text/html,application/json,text/plain,application/xml,text/xml;q=0.9",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            host = (urlparse(response.geturl()).hostname or "").lower()
            if host not in source.allowed_hosts:
                raise ValidationError(
                    f"{source.source_id}: redirect landed on a non-allowlisted host: {host}"
                )

            content_type = _content_type(response.headers.get("Content-Type"))
            if content_type not in source.content_types:
                raise ValidationError(
                    f"{source.source_id}: unsupported content-type {content_type!r}"
                )

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_response_bytes:
                raise ValidationError(
                    f"{source.source_id}: response exceeds {max_response_bytes} bytes"
                )

            content = response.read(max_response_bytes + 1)
            if len(content) > max_response_bytes:
                raise ValidationError(
                    f"{source.source_id}: response exceeds {max_response_bytes} bytes"
                )

            normalized = normalize_content(
                content,
                content_type,
                response.headers.get_content_charset(),
            )
            return normalized, status, content_type

    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"network error: {exc.reason}") from exc


def signed_webhook_body(payload: dict[str, Any], secret: str) -> tuple[bytes, str]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, f"sha256={signature}"


def send_webhook(url: str, secret: str, payload: dict[str, Any], timeout: int) -> None:
    body, signature = signed_webhook_body(payload, secret)
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "X-ClearGlass-Signature": signature,
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        if not 200 <= int(response.status) < 300:
            raise RuntimeError(f"webhook returned HTTP {response.status}")


def run(
    registry_path: Path,
    state_path: Path,
    *,
    dry_run: bool,
    webhook_url: str | None,
    webhook_secret: str | None,
) -> dict[str, Any]:
    policy, sources = load_registry(registry_path)
    state = load_state(state_path)
    now = int(time.time())
    events: list[dict[str, Any]] = []

    if webhook_url and not webhook_secret:
        raise ValidationError("webhook_url requires an HMAC webhook secret")

    for source in sources:
        try:
            normalized, status, content_type = fetch_source(
                source,
                policy["default_timeout_seconds"],
                policy["max_response_bytes"],
            )
            current_hash = fingerprint(normalized)
            previous = state["sources"].get(source.source_id)
            event_type = "initialized" if previous is None else (
                "changed" if previous.get("sha256") != current_hash else "unchanged"
            )

            record = {
                "authority": source.authority,
                "url": source.url,
                "sha256": current_hash,
                "status": status,
                "content_type": content_type,
                "observed_at": now,
                "event_type": event_type,
            }

            if not dry_run:
                state["sources"][source.source_id] = record

            if event_type == "changed":
                event = {
                    "event": "strait_watch_change",
                    "source_id": source.source_id,
                    "authority": source.authority,
                    "url": source.url,
                    "previous_sha256": previous.get("sha256"),
                    "current_sha256": current_hash,
                    "observed_at": now,
                    "requires_human_verification": True,
                }
                events.append(event)
                if webhook_url and webhook_secret:
                    send_webhook(
                        webhook_url,
                        webhook_secret,
                        event,
                        policy["default_timeout_seconds"],
                    )
            else:
                events.append(
                    {
                        "event": f"strait_watch_{event_type}",
                        "source_id": source.source_id,
                        "authority": source.authority,
                        "url": source.url,
                        "sha256": current_hash,
                        "observed_at": now,
                    }
                )

        except Exception as exc:
            event = {
                "event": "strait_watch_error",
                "source_id": source.source_id,
                "authority": source.authority,
                "url": source.url,
                "error": str(exc),
                "observed_at": now,
                "requires_human_verification": True,
            }
            events.append(event)
            if not dry_run:
                current = state["sources"].get(source.source_id, {})
                current["last_error"] = str(exc)
                current["last_error_at"] = now
                state["sources"][source.source_id] = current

    if not dry_run:
        state["last_run_at"] = now
        state["registry_version"] = policy["version"]
        save_state(state_path, state)

    return {
        "dry_run": dry_run,
        "registry": str(registry_path),
        "state": str(state_path),
        "events": events,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sources", type=Path, default=Path("data/strait-watch/sources.json"))
    parser.add_argument("--state", type=Path, default=Path(".data/strait-watch/state.json"))
    parser.add_argument("--dry-run", action="store_true", help="do not write state and do not send webhooks")
    parser.add_argument(
        "--webhook-url",
        default=os.environ.get("CLEARGLASS_STRAIT_WATCH_WEBHOOK_URL"),
    )
    parser.add_argument(
        "--webhook-secret-env",
        default="CLEARGLASS_STRAIT_WATCH_WEBHOOK_SECRET",
        help="environment variable containing the webhook HMAC secret",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    secret = os.environ.get(args.webhook_secret_env) if args.webhook_url else None
    try:
        result = run(
            args.sources,
            args.state,
            dry_run=args.dry_run,
            webhook_url=args.webhook_url,
            webhook_secret=secret,
        )
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
