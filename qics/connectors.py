"""External source connectors. Fail closed. Not operational until a fetch is proven."""

from __future__ import annotations

from dataclasses import dataclass

from .schema import FailClosed


@dataclass(frozen=True)
class FetchResult:
    source_id: str
    status: str
    http_status: int | None
    body_hash: str | None
    error: str | None


ALLOWED_HOSTS = frozenset(
    {
        "csrc.nist.gov",
        "www.nist.gov",
        "www.cisa.gov",
        "www.cyber.gc.ca",
    }
)


def fetch_source(url: str, *, allow_network: bool = False) -> FetchResult:
    """Live HTTP is off by default. Network is untrusted and optional."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        return FetchResult(
            source_id=url,
            status=FailClosed.SOURCE_UNAVAILABLE.value,
            http_status=None,
            body_hash=None,
            error="host_not_allowlisted",
        )
    if not allow_network:
        return FetchResult(
            source_id=url,
            status=FailClosed.SOURCE_UNAVAILABLE.value,
            http_status=None,
            body_hash=None,
            error="network_disabled",
        )
    # Live fetch is intentionally unimplemented in v2.0 so a failed or
    # injected response cannot become VERIFIED evidence.
    return FetchResult(
        source_id=url,
        status=FailClosed.SOURCE_UNAVAILABLE.value,
        http_status=None,
        body_hash=None,
        error="live_fetch_not_implemented",
    )
