"""Protect verified Intelligence Graph metrics from fabricated fallbacks.

The graph loads an integrity-checked collector snapshot. Missing analytics are
unavailable, not a hard-coded 'live' value; real zero values remain visible.
"""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "assets/intelligence-graph/graph.js").read_text(encoding="utf-8")


def test_missing_model_count_has_no_fabricated_default() -> None:
    assert 's.model_count??analytics.model_count??"—"' in SOURCE
    assert "s.model_count??analytics.model_count??7" not in SOURCE


def test_zero_density_is_not_treated_as_missing() -> None:
    assert "Number.isFinite(density)?" in SOURCE
    assert "Number.isFinite(density)&&density?" not in SOURCE


def test_missing_reach_is_not_displayed_as_zero() -> None:
    assert "reach!=null&&Number.isFinite(Number(reach))?" in SOURCE


def test_graph_still_validates_snapshot_before_rendering() -> None:
    assert "const r=await verifySnapshot(s);" in SOURCE
    assert "if(!r.ok)" in SOURCE
    assert "renderExecutive(s);" in SOURCE
