from artemis_platform.self_evolving_platform import (
    EnvironmentalCyberRiskSignal,
    environmental_cyber_risk_assessment,
)


def test_environmental_cyber_risk_threshold_bands():
    green = environmental_cyber_risk_assessment(
        EnvironmentalCyberRiskSignal(
            "s-green", "burlington-1", 5.39, 2.0, 0.1, 1.0, 1.5
        )
    )
    yellow_low = environmental_cyber_risk_assessment(
        EnvironmentalCyberRiskSignal(
            "s-yellow-low", "burlington-1", 5.40, 3.0, 0.2, 2.0, 2.5
        )
    )
    yellow_high = environmental_cyber_risk_assessment(
        EnvironmentalCyberRiskSignal(
            "s-yellow-high", "burlington-1", 5.80, 4.0, 0.4, 5.0, 5.0
        )
    )
    red = environmental_cyber_risk_assessment(
        EnvironmentalCyberRiskSignal("s-red", "burlington-1", 5.81, 7.0, 0.7, 9.0, 12.0)
    )

    assert green.band == "GREEN"
    assert yellow_low.band == "YELLOW"
    assert yellow_high.band == "YELLOW"
    assert red.band == "RED"
    assert "HF_COMMUNICATIONS" in red.affected_services
    assert any("Gotham case" in step for step in red.mitigation_playbook)
