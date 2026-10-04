from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .registry import get_source, list_sources

router = APIRouter(prefix="/v1/osint", tags=["ARTEMIS OSINT"])


@router.get("/health")
def osint_health() -> dict[str, int | str]:
    sources = list_sources()
    enabled = sum(1 for source in sources if source.enabled_by_default)
    return {
        "status": "ready",
        "service": "artemis-osint-fabric",
        "sources": len(sources),
        "phase_1_enabled": enabled,
    }


@router.get("/sources")
def osint_sources(phase: int | None = None) -> list[dict]:
    return [source.model_dump() for source in list_sources(phase=phase)]


@router.get("/sources/{source_id}")
def osint_source(source_id: str) -> dict:
    try:
        return get_source(source_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
