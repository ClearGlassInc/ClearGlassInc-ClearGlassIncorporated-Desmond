from artemis_platform.self_evolving_platform import (
    ElectricalFinding,
    build_electrical_work_order,
    classify_electrical_finding,
)


def test_immediate_danger_requires_isolation_controls() -> None:
    finding = ElectricalFinding(
        finding_id="panel-001",
        asset_id="PANEL-MDP-01",
        description="Documented burning odour at distribution equipment.",
        evidence_refs=("photo://panel-001",),
        observed_hazards=frozenset({"burning_odour", "incorrect_panel_directory"}),
    )

    work_order = build_electrical_work_order(finding)

    assert classify_electrical_finding(finding) == "immediate_danger"
    assert work_order.severity == "immediate_danger"
    assert "lockout/tagout" in work_order.required_controls
    assert "live-dead-live" in " ".join(work_order.required_controls)
    assert "isolate" in work_order.repair_objective


def test_labeling_defect_is_code_correction_not_cosmetic_cleanup() -> None:
    finding = ElectricalFinding(
        finding_id="dir-002",
        asset_id="PANEL-LP-02",
        description="Panel directory does not match traced circuit register.",
        evidence_refs=("trace-register://lp-02",),
        observed_hazards=frozenset({"incorrect_panel_directory"}),
    )

    work_order = build_electrical_work_order(finding)

    assert work_order.severity == "code_correction"
    assert "Applicable permit and inspection requirements" in work_order.final_report_sections
    assert "Exact test results" in work_order.final_report_sections
