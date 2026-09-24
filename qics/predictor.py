"""Opportunity predictor. Missing classical baseline -> no quantum-advantage claim."""

from __future__ import annotations

from typing import Any

from .schema import FailClosed, Opportunity, OpportunityKind, ScoreBreakdown


def predict(
    score: ScoreBreakdown,
    *,
    classical_baseline: dict[str, Any] | None = None,
    want_quantum_advantage_claim: bool = False,
) -> list[Opportunity]:
    tenant_id = score.tenant_id
    out: list[Opportunity] = []

    if want_quantum_advantage_claim:
        required = {"CURRENT_COST", "CURRENT_LATENCY", "CURRENT_ACCURACY", "CURRENT_THROUGHPUT", "QUANTUM_METHOD"}
        present = set((classical_baseline or {}).keys())
        if not classical_baseline or not required.issubset(present):
            out.append(
                Opportunity(
                    kind=OpportunityKind.HYPOTHETICAL.value,
                    title="Quantum-advantage comparison",
                    assumption_list=["Classical baseline fields missing."],
                    financial_projection_guaranteed=False,
                    classical_baseline=classical_baseline,
                    tenant_id=tenant_id,
                    status=FailClosed.INSUFFICIENT_BASELINE_DATA.value,
                )
            )
            return out

    if score.rating in {"HIGH_EXPOSURE", "CRITICAL_EXPOSURE"}:
        out.append(
            Opportunity(
                kind=OpportunityKind.OBSERVED.value,
                title="Cryptographic inventory and PQC migration planning",
                assumption_list=[
                    "Buyer has not completed a PQC plan.",
                    "Price and hours are not estimated here.",
                ],
                financial_projection_guaranteed=False,
                classical_baseline=classical_baseline,
                tenant_id=tenant_id,
            )
        )
    elif score.rating == "INSUFFICIENT_DATA":
        out.append(
            Opportunity(
                kind=OpportunityKind.DERIVED.value,
                title="Complete a cryptographic asset register",
                assumption_list=["Opportunity exists only if the tenant lacks an inventory."],
                financial_projection_guaranteed=False,
                classical_baseline=classical_baseline,
                tenant_id=tenant_id,
            )
        )
    else:
        out.append(
            Opportunity(
                kind=OpportunityKind.HYPOTHETICAL.value,
                title="Periodic inventory refresh",
                assumption_list=["No observed high exposure in the declared inventory."],
                financial_projection_guaranteed=False,
                classical_baseline=classical_baseline,
                tenant_id=tenant_id,
            )
        )
    return out
