# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Allowlisted HTTP connector with SSRF controls and response limits."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Mapping
from urllib.parse import urlparse

import httpx

from .base import ConnectorError, ConnectorResponse


class AllowlistedHTTPConnector:
    name = "http"

    def __init__(
        self,
        allowed_hosts: set[str],
        *,
        timeout_seconds: float = 20.0,
        max_response_bytes: int = 2_000_000,
        allow_private_networks: bool = False,
    ) -> None:
        self.allowed_hosts = {host.casefold().rstrip(".") for host in allowed_hosts}
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.allow_private_networks = allow_private_networks

    async def health(self) -> ConnectorResponse:
        return ConnectorResponse(
            connector=self.name,
            operation="health",
            data={"allowed_hosts": sorted(self.allowed_hosts)},
        )

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: object | None = None,
    ) -> dict[str, object]:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ConnectorError("Only HTTPS URLs are permitted")
        if parsed.username or parsed.password:
            raise ConnectorError("Credentials in URLs are not permitted")
        host = (parsed.hostname or "").casefold().rstrip(".")
        if host not in self.allowed_hosts:
            raise ConnectorError(f"Host is not allowlisted: {host or '<missing>'}")
        if parsed.port not in (None, 443):
            raise ConnectorError("Only the standard HTTPS port is permitted")
        await self._validate_addresses(host)

        normalized_method = method.upper()
        if normalized_method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
            raise ConnectorError(f"HTTP method is not supported: {normalized_method}")
        clean_headers = {
            str(key): str(value)
            for key, value in (headers or {}).items()
            if key.casefold() not in {"host", "content-length", "transfer-encoding"}
        }

        timeout = httpx.Timeout(self.timeout_seconds)
        async with (
            httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client,
            client.stream(
                normalized_method,
                url,
                headers=clean_headers,
                json=json_body,
            ) as response,
        ):
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > self.max_response_bytes:
                    raise ConnectorError(
                        f"Response exceeded {self.max_response_bytes} byte limit"
                    )
                chunks.append(chunk)
            body = b"".join(chunks)

        return {
            "url": str(response.url),
            "status_code": response.status_code,
            "headers": {
                key: value
                for key, value in response.headers.items()
                if key.casefold() not in {"set-cookie", "authorization", "proxy-authorization"}
            },
            "body": body.decode("utf-8", errors="replace"),
            "bytes": len(body),
        }

    async def _validate_addresses(self, host: str) -> None:
        if self.allow_private_networks:
            return
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise ConnectorError(f"Host resolves to a non-public address: {ip}")
