from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import httpx

from .models import ProvenanceRecord, SourceDefinition
from .registry import get_source

logger = logging.getLogger("artemis.osint")


class ConnectorDisabled(RuntimeError):
    """Raised when a source cannot be safely automated in the current mode."""


class SourceHTTPError(RuntimeError):
    """Raised after retryable HTTP failures are exhausted."""


class RateLimiter:
    def __init__(self, rate_rps: float | None) -> None:
        self.interval = 1.0 / rate_rps if rate_rps and rate_rps > 0 else 0.0
        self._next_allowed = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        if self.interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_allowed - now)
            self._next_allowed = max(now, self._next_allowed) + self.interval
        if delay:
            await asyncio.sleep(delay)


class HttpSourceConnector:
    """Generic read-only connector for every source with an approved HTTP API/feed."""

    RETRYABLE = {429, 500, 502, 503, 504}

    def __init__(
        self,
        source: SourceDefinition,
        *,
        timeout: float = 20.0,
        max_retries: int = 3,
        user_agent: str = "ClearGlass-ARTEMIS-OSINT/1.0 (+https://clearglassinc.com)",
    ) -> None:
        self.source = source
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.rate_limiter = RateLimiter(source.rate_limit_rps)

    @classmethod
    def for_source(cls, source_id: str, **kwargs: Any) -> "HttpSourceConnector":
        return cls(get_source(source_id), **kwargs)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, application/geo+json;q=0.9, text/plain;q=0.7, */*;q=0.5",
            "User-Agent": self.user_agent,
        }
        auth_env = self.source.auth_env
        if auth_env:
            import os

            token = os.getenv(auth_env)
            if not token:
                raise ConnectorDisabled(
                    f"{self.source.source_id} requires runtime credential {auth_env}; "
                    "no secret is stored in the repository"
                )
            if self.source.authentication.lower().startswith("bearer"):
                headers["Authorization"] = f"Bearer {token}"
        return headers

    def _params(self, params: dict[str, Any] | None) -> dict[str, Any]:
        params = dict(params or {})
        auth_env = self.source.auth_env
        if auth_env and self.source.authentication.lower().startswith("api key"):
            import os

            token = os.getenv(auth_env)
            if not token:
                raise ConnectorDisabled(
                    f"{self.source.source_id} requires runtime credential {auth_env}"
                )
            params.setdefault("api_key", token)
        return params

    async def fetch(
        self,
        *,
        url: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, ProvenanceRecord, httpx.Headers]:
        if self.source.adapter in {"web_link_only", "reference_only", "file_import"}:
            raise ConnectorDisabled(
                f"{self.source.name} is not approved for automated web scraping or harvesting"
            )
        target = url or self.source.endpoint
        if not target:
            raise ConnectorDisabled(f"{self.source.name} has no automated endpoint")
        headers = self._headers()
        request_params = self._params(params)

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for attempt in range(self.max_retries + 1):
                await self.rate_limiter.wait()
                try:
                    response = await client.get(target, headers=headers, params=request_params)
                except httpx.RequestError as exc:
                    if attempt >= self.max_retries:
                        raise SourceHTTPError(f"{self.source.name}: request failed") from exc
                    await asyncio.sleep(self._backoff(attempt))
                    continue

                if response.status_code in self.RETRYABLE and attempt < self.max_retries:
                    retry_after = self._retry_after(response.headers)
                    await asyncio.sleep(
                        retry_after if retry_after is not None else self._backoff(attempt)
                    )
                    continue

                if response.status_code >= 400:
                    raise SourceHTTPError(f"{self.source.name}: HTTP {response.status_code}")

                payload = self._decode(response)
                provenance = ProvenanceRecord.from_payload(
                    self.source,
                    payload,
                    retrieved_via="official_api",
                    source_url=str(response.url),
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )
                logger.info(
                    "ingested source=%s status=%s sha256=%s",
                    self.source.source_id,
                    response.status_code,
                    provenance.content_sha256,
                )
                return payload, provenance, response.headers

        raise SourceHTTPError(f"{self.source.name}: exhausted retry budget")

    @staticmethod
    def _decode(response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "").lower()
        if "json" in content_type or response.text.lstrip().startswith(("{", "[")):
            return response.json()
        return {"text": response.text}

    @staticmethod
    def _retry_after(headers: httpx.Headers) -> float | None:
        value = headers.get("retry-after")
        if not value:
            return None
        try:
            return min(float(value), 60.0)
        except ValueError:
            return None

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(30.0, (2**attempt) + random.uniform(0, 0.25))


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, HttpSourceConnector] = {}

    def get(self, source_id: str) -> HttpSourceConnector:
        if source_id not in self._connectors:
            self._connectors[source_id] = HttpSourceConnector.for_source(source_id)
        return self._connectors[source_id]

    def capability_matrix(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": source.source_id,
                "adapter": source.adapter,
                "enabled_by_default": source.enabled_by_default,
                "network": source.adapter not in {"web_link_only", "reference_only", "file_import"},
            }
            for source in sorted((get_source(s.source_id) for s in self._connectors.values()), key=lambda x: x.name)
        ]
