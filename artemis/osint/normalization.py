from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .models import EventRecord, LocationRecord, ObservationRecord, ProvenanceRecord


def _location_from_geometry(geometry: dict[str, Any] | None) -> LocationRecord | None:
    if not geometry or geometry.get("type") != "Point":
        return None
    coordinates = geometry.get("coordinates") or []
    if len(coordinates) < 2:
        return None
    lon, lat = float(coordinates[0]), float(coordinates[1])
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return LocationRecord(location_id=str(uuid4()), latitude=lat, longitude=lon)


def normalize_geojson(
    source_id: str,
    payload: dict[str, Any],
    provenance: ProvenanceRecord,
) -> tuple[list[ObservationRecord], list[EventRecord]]:
    observations: list[ObservationRecord] = []
    events: list[EventRecord] = []
    features = payload.get("features", [])
    if payload.get("type") == "Feature":
        features = [payload]
    for feature in features:
        props = dict(feature.get("properties") or {})
        observed_raw = props.get("time") or props.get("datetime") or provenance.retrieved_at.isoformat()
        try:
            if isinstance(observed_raw, (int, float)):
                observed_at = datetime.fromtimestamp(observed_raw / 1000, tz=UTC)
            else:
                observed_at = datetime.fromisoformat(str(observed_raw).replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            observed_at = provenance.retrieved_at
        location = _location_from_geometry(feature.get("geometry"))
        event_type = str(props.get("type") or props.get("eventtype") or "feature")
        title = props.get("place") or props.get("title") or props.get("name")
        events.append(
            EventRecord(
                event_id=str(uuid4()),
                source_id=source_id,
                event_type=event_type,
                occurred_at=observed_at,
                title=str(title) if title is not None else None,
                location=location,
                attributes=props,
                provenance=provenance,
            )
        )
        observations.append(
            ObservationRecord(
                observation_id=str(uuid4()),
                source_id=source_id,
                observed_at=observed_at,
                kind=event_type,
                value=props,
                location=location,
                provenance=provenance,
            )
        )
    return observations, events
