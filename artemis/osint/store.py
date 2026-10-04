from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .models import EventRecord, ObservationRecord, SourceDefinition


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    categories_json TEXT NOT NULL,
    integration_mode TEXT NOT NULL,
    public_api TEXT NOT NULL,
    authentication TEXT NOT NULL,
    rate_limit TEXT NOT NULL,
    license TEXT NOT NULL,
    terms_concern TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    update_frequency TEXT NOT NULL,
    ingestion_method TEXT NOT NULL,
    endpoint TEXT,
    adapter TEXT NOT NULL,
    phase INTEGER NOT NULL,
    enabled_by_default INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS provenance (
    content_sha256 TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_url TEXT,
    retrieved_at TEXT NOT NULL,
    retrieved_via TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    etag TEXT,
    last_modified TEXT,
    license_snapshot TEXT NOT NULL,
    terms_snapshot TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    value_json TEXT NOT NULL,
    provenance_sha256 TEXT NOT NULL REFERENCES provenance(content_sha256)
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    title TEXT,
    attributes_json TEXT NOT NULL,
    provenance_sha256 TEXT NOT NULL REFERENCES provenance(content_sha256)
);
"""


class SQLiteStore:
    """Development/test store. Production persistence is defined in schema.sql."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.executescript(SCHEMA)

    def upsert_sources(self, sources: Iterable[SourceDefinition]) -> None:
        import json

        for source in sources:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO sources (
                    source_id,name,categories_json,integration_mode,public_api,authentication,
                    rate_limit,license,terms_concern,metadata_json,update_frequency,
                    ingestion_method,endpoint,adapter,phase,enabled_by_default
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    source.source_id,
                    source.name,
                    json.dumps(source.categories),
                    source.integration_mode,
                    source.public_api,
                    source.authentication,
                    source.rate_limit,
                    source.license,
                    source.terms_concern,
                    json.dumps(source.metadata),
                    source.update_frequency,
                    source.ingestion_method,
                    source.endpoint,
                    source.adapter,
                    source.phase,
                    int(source.enabled_by_default),
                ),
            )
        self._conn.commit()

    def write_observations(
        self, observations: Iterable[ObservationRecord], events: Iterable[EventRecord]
    ) -> None:
        import json

        for observation in observations:
            p = observation.provenance
            self._conn.execute(
                "INSERT OR IGNORE INTO provenance VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    p.content_sha256,
                    p.source_id,
                    p.source_url,
                    p.retrieved_at.isoformat(),
                    p.retrieved_via,
                    p.parser_version,
                    p.etag,
                    p.last_modified,
                    p.license_snapshot,
                    p.terms_snapshot,
                ),
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO observations VALUES (?,?,?,?,?,?)",
                (
                    observation.observation_id,
                    observation.source_id,
                    observation.observed_at.isoformat(),
                    observation.kind,
                    json.dumps(observation.value, default=str),
                    p.content_sha256,
                ),
            )
        for event in events:
            p = event.provenance
            self._conn.execute(
                "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.source_id,
                    event.event_type,
                    event.occurred_at.isoformat(),
                    event.title,
                    json.dumps(event.attributes, default=str),
                    p.content_sha256,
                ),
            )
        self._conn.commit()
