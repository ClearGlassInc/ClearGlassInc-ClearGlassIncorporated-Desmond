from artemis.environmental.risk import EnvironmentalObservation, dashboard_snapshot, classify_log_nf2


def test_log_nf2_threshold_contract_boundaries() -> None:
    assert classify_log_nf2(5.39)[0] == "GREEN"
    assert classify_log_nf2(5.40)[0] == "YELLOW"
    assert classify_log_nf2(5.80)[0] == "YELLOW"
    assert classify_log_nf2(5.81)[0] == "RED"


def test_dashboard_snapshot_contains_actionable_vectors() -> None:
    snapshot = dashboard_snapshot(EnvironmentalObservation(log_nf2=5.92))

    assert snapshot["band"] == "RED"
    assert len(snapshot["threat_vectors"]) == 3
    assert {row.vector for row in snapshot["threat_vectors"]} == {"GNSS/GPS", "HF Radio", "OTHR Radar"}
    assert all(row.mitigation for row in snapshot["threat_vectors"])
