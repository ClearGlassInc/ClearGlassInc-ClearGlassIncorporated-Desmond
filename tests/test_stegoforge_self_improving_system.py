# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.stegoforge_self_improving_system import Event, Principal, Stage, StegoForgeSystem


def test_process_event_generates_approved_actions():
    system = StegoForgeSystem()
    principal = Principal(
        user_id="analyst-1",
        missions={"mission-alpha"},
        coalition_domain="FVEY",
        clearance="SECRET",
    )
    event = Event(
        event_id="evt-1",
        mission_id="mission-alpha",
        coalition_domain="FVEY",
        payload={"signals": 6, "entities": ["host-a"], "campaign": "griffin"},
    )

    run = system.process_event(principal, event)

    assert run.stage == Stage.CLOSED
    assert "Isolate affected segment" in run.approved_actions
    assert "Notify cross-coalition partner" in run.rejected_actions


def test_improvement_proposal_requires_human_approval():
    system = StegoForgeSystem()
    principal = Principal(
        user_id="analyst-2",
        missions={"mission-beta"},
        coalition_domain="FVEY",
        clearance="SECRET",
    )
    event = Event(
        event_id="evt-2",
        mission_id="mission-beta",
        coalition_domain="FVEY",
        payload={"signals": 8, "entities": ["host-b"], "campaign": "unknown"},
    )

    system.process_event(principal, event)
    proposal = system.improvement_proposal()

    assert proposal["requires_human_approval"] is True
    assert proposal["commander_rejects"] >= 0
