import pytest

# artemis.osint needs pydantic and httpx. A bare import made this module a
# collection error wherever they were missing, which aborted the whole root
# suite; ci.yml installs both so these tests still run there.
pytest.importorskip("pydantic")
pytest.importorskip("httpx")

from artemis.osint.connectors import ConnectorDisabled, HttpSourceConnector  # noqa: E402
from artemis.osint.models import ProvenanceRecord  # noqa: E402
from artemis.osint.normalization import normalize_geojson  # noqa: E402
from artemis.osint.registry import SOURCE_DEFINITIONS, get_source, list_sources  # noqa: E402


def test_registry_contains_all_requested_sources():
    assert len(SOURCE_DEFINITIONS) == 30
    assert len({source.source_id for source in SOURCE_DEFINITIONS}) == 30


def test_phase_one_sources_are_enabled_by_default():
    expected = {
        "openstreetmap",
        "usgs-earthquakes",
        "nasa-apod",
        "nasa-image-library",
        "our-world-in-data",
        "world-bank-open-data",
    }
    actual = {source.source_id for source in SOURCE_DEFINITIONS if source.enabled_by_default}
    assert actual == expected


def test_web_only_connector_fails_closed():
    import asyncio

    connector = HttpSourceConnector.for_source("atlas-obscura")
    try:
        asyncio.run(connector.fetch())
    except ConnectorDisabled:
        pass
    else:
        raise AssertionError("web-only source unexpectedly allowed network automation")


def test_geojson_normalization_preserves_provenance():
    source = get_source("usgs-earthquakes")
    provenance = ProvenanceRecord.from_payload(
        source,
        {"type": "FeatureCollection", "features": []},
        retrieved_via="test",
    )
    observations, events = normalize_geojson(
        "usgs-earthquakes",
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-79.38, 43.65]},
                    "properties": {"mag": 2.1, "place": "Toronto", "time": 1760000000000},
                }
            ],
        },
        provenance,
    )
    assert len(observations) == 1
    assert len(events) == 1
    assert observations[0].provenance.content_sha256 == provenance.content_sha256
    assert observations[0].location is not None
    assert observations[0].location.longitude == -79.38


def test_phase_filter():
    assert all(source.phase == 1 for source in list_sources(phase=1))
