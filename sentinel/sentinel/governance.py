"""SENTINEL — Governance Shell.

Implements the SABER-aligned, fail-closed assurance gate:

    Execution = Permitted  iff  (C >= tau) AND (R_data ⊆ P_user) AND (S_threat < eps)
              = Denied     otherwise

Doctrine: if ANY variable cannot be computed (e.g. an RBAC/DB timeout while
resolving P_user, or the red-team scorer raising), the gate returns DENIED.
Unverifiable is never treated as permitted.
"""
from __future__ import annotations

from typing import Optional

from .models import AssuranceDecision, AssuranceThresholds, Decision


def assess(
    *,
    confidence: Optional[float],
    threat_score: Optional[float],
    data_in_scope: Optional[bool],
    thresholds: AssuranceThresholds = AssuranceThresholds(),
) -> AssuranceDecision:
    """Evaluate the boolean assurance gate, fail-closed.

    Parameters mirror the equation variables:
      * ``confidence``    -> C   (None == unverifiable -> deny)
      * ``threat_score``  -> S_threat (None == unverifiable -> deny)
      * ``data_in_scope`` -> truthiness of (R_data ⊆ P_user); None -> deny
    """
    try:
        if confidence is None:
            return _deny("confidence unavailable (fail-closed)", None, threat_score)
        if threat_score is None:
            return _deny("threat score unavailable (fail-closed)", confidence, None)
        if data_in_scope is None:
            return _deny("permission boundary unverifiable (fail-closed)", confidence, threat_score)

        ok_conf = confidence >= thresholds.tau
        ok_scope = bool(data_in_scope)
        ok_threat = threat_score < thresholds.epsilon

        if ok_conf and ok_scope and ok_threat:
            return AssuranceDecision(
                Decision.PERMITTED,
                ("C>=tau", "R_data⊆P_user", "S_threat<epsilon"),
                confidence,
                threat_score,
            )

        reasons: list[str] = []
        if not ok_conf:
            reasons.append(f"confidence {confidence:.2f} < tau {thresholds.tau:.2f}")
        if not ok_scope:
            reasons.append("requested data exceeds permission boundary (R_data ⊄ P_user)")
        if not ok_threat:
            reasons.append(f"threat {threat_score:.2f} >= epsilon {thresholds.epsilon:.2f}")
        return AssuranceDecision(Decision.DENIED, tuple(reasons), confidence, threat_score)
    except Exception as exc:  # any computation failure -> fail-closed
        return AssuranceDecision(
            Decision.DENIED,
            (f"assurance check raised {type(exc).__name__}: fail-closed",),
            None,
            None,
        )


def _deny(reason: str, c: Optional[float], s: Optional[float]) -> AssuranceDecision:
    return AssuranceDecision(Decision.DENIED, (reason,), c, s)
