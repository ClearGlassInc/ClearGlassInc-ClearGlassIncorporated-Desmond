from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_artemis_mesh_exposes_all_governed_platform_layers() -> None:
    page = (ROOT / "sentinel.html").read_text(encoding="utf-8")

    assert 'id="fusionLayer"' in page
    assert 'aria-controls="fusionLayer"' in page
    for platform in ("GOTHAM", "FOUNDRY", "AIP", "APOLLO"):
        assert f"<b>{platform}</b>" in page


def test_artemis_blueprint_keeps_improvements_human_governed() -> None:
    page = (ROOT / "sentinel.html").read_text(encoding="utf-8")

    assert "consequential actions require human approval" in page
    assert "not evidence of a provisioned Palantir environment" in page
    assert "Require human approval for promotion" in page
    assert "OBSERVE → CORRELATE → DRAFT → POLICY CHECK → HUMAN REVIEW → EXECUTE → AUDIT" in page


def test_artemis_animation_respects_reduced_motion() -> None:
    page = (ROOT / "sentinel.html").read_text(encoding="utf-8")

    assert "@media(prefers-reduced-motion:reduce)" in page
    assert ".fusion-grid::before,.fusion-core::after" in page
    assert "{animation:none!important}" in page
