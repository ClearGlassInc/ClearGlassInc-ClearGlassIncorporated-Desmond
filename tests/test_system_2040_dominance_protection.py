from artemis_platform.self_evolving_platform import EnvironmentalCyberRiskSignal
from artemis_platform.system_2040_dominance_protection import (
    ActionGate,
    GovernedAccessBroker,
    GovernedDominancePushEngine,
    MissionPrincipal,
    System2040AutomationLoop,
    System2040ProtectionEngine,
)


def _principal() -> MissionPrincipal:
    return MissionPrincipal(
        actor_id="operator-2040",
        mission_id="mission-burlington-resilience",
        purpose="infrastructure_defense",
        clearance="CUI",
        compartments=frozenset({"ENVIRONMENTAL_CYBER_RISK"}),
        approved_resources=frozenset({"environmental.telemetry.phase1"}),
    )


def test_system_2040_uses_governed_access_not_skeleton_key():
    broker = GovernedAccessBroker()
    engine = System2040ProtectionEngine(broker)
    signal = EnvironmentalCyberRiskSignal(
        signal_id="red-001",
        site_id="burlington-command",
        log_nm_f2=5.91,
        kp_index=6.0,
        scintillation_s4=0.6,
        hf_absorption_db=9.0,
        gnss_error_m=14.0,
    )

    finding = engine.assess_ionospheric_signal(_principal(), signal)

    assert finding.severity == "RED"
    assert broker.audit_log[-1].details["allowed"] is True
    assert "no_secret_materialization" in broker.audit_log[-1].details["obligations"]


def test_unauthorized_resource_is_denied_before_scoring():
    broker = GovernedAccessBroker()
    engine = System2040ProtectionEngine(broker)
    principal = MissionPrincipal(
        actor_id="operator-2040",
        mission_id="mission-burlington-resilience",
        purpose="infrastructure_defense",
        clearance="CUI",
        compartments=frozenset({"ENVIRONMENTAL_CYBER_RISK"}),
        approved_resources=frozenset(),
    )
    signal = EnvironmentalCyberRiskSignal("blocked", "burlington", 5.5, 4.0, 0.2, 3.0, 4.0)

    try:
        engine.assess_ionospheric_signal(principal, signal)
    except PermissionError as exc:
        assert "not mission-entitled" in str(exc)
    else:
        raise AssertionError("expected access denial")


def test_red_mitigation_and_growth_packages_require_human_approval():
    broker = GovernedAccessBroker()
    loop = System2040AutomationLoop(
        System2040ProtectionEngine(broker),
        GovernedDominancePushEngine(),
    )
    signal = EnvironmentalCyberRiskSignal("red-002", "burlington", 5.88, 6.0, 0.5, 8.0, 11.0)

    result = loop.run_once(_principal(), signal)
    protection, growth = result["action_packages"]

    assert protection.gate is ActionGate.OPERATIONAL_EFFECT
    assert protection.status == "pending_human_approval"
    assert protection.requires_human_approval is True
    assert growth.gate is ActionGate.REVENUE_PUBLICATION
    assert growth.status == "pending_human_approval"
    assert growth.requires_human_approval is True
