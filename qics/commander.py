"""Quantum Commander — orchestration only. Cannot change production crypto."""

from __future__ import annotations

from typing import Any

from . import metrics
from .advisor import advise
from .audit import AppendOnlyAudit, make_event
from .catalog import bundled_catalog
from .connectors import fetch_source
from .evidence import detect_conflicts, hypothesis_item, require_tenant
from .predictor import predict
from .scanner import scan_inventory
from .schema import ApprovalRecord, Inventory


class QuantumCommander:
    def __init__(self, audit: AppendOnlyAudit | None = None) -> None:
        self.audit = audit or AppendOnlyAudit()
        self._approvals: list[ApprovalRecord] = []

    def run(
        self,
        inventory: Inventory,
        *,
        actor: str = "qics",
        classical_baseline: dict[str, Any] | None = None,
        want_quantum_advantage_claim: bool = False,
        live_fetch: bool = False,
    ) -> dict[str, Any]:
        tenant_id = require_tenant(inventory.tenant_id)
        metrics.inc("qics_scanner_runs_total")

        evidence = bundled_catalog(tenant_id)
        metrics.inc("qics_evidence_items_total", len(evidence))
        metrics.inc("qics_ingestion_success_total")

        if live_fetch:
            for item in evidence:
                result = fetch_source(item.source_url, allow_network=True)
                if result.status != "ok":
                    metrics.inc("qics_ingestion_failure_total")

        conflicts = detect_conflicts(evidence)
        if conflicts:
            metrics.inc("qics_conflicting_claims_total", len(conflicts))

        score = scan_inventory(inventory)
        recs = advise(score)
        metrics.inc("qics_recommendations_total", len(recs))
        opportunities = predict(
            score,
            classical_baseline=classical_baseline,
            want_quantum_advantage_claim=want_quantum_advantage_claim,
        )

        pending = [r for r in recs if r.human_approval_required and r.status == "PENDING_APPROVAL"]
        metrics.inc("qics_approval_requests_total", len(pending))

        event = make_event(
            tenant_id=tenant_id,
            actor=actor,
            agent="quantum-commander",
            action="qics.run",
            payload={"rating": score.rating, "rec_count": len(recs)},
            previous_state="idle",
            new_state=score.rating,
            decision="scored",
            confidence=score.confidence,
        )
        self.audit.append(event)

        return {
            "tenant_id": tenant_id,
            "score": score.to_dict(),
            "recommendations": [r.to_dict() for r in recs],
            "opportunities": [o.to_dict() for o in opportunities],
            "evidence": [e.to_dict() for e in evidence],
            "conflicts": [c.to_dict() for c in conflicts],
            "approval_required": bool(pending),
            "audit_event_id": event.event_id,
            "metrics": metrics.snapshot(),
            "connectors": {
                "nist": "SOURCE_UNAVAILABLE",
                "note": "Live connectors are not operational in v2.0.",
            },
        }

    def approve(
        self,
        *,
        tenant_id: str,
        request_id: str,
        actor: str,
        role: str,
        action: str,
        reason: str,
        evidence_version: str,
        decision: str,
    ) -> ApprovalRecord:
        tenant_id = require_tenant(tenant_id)
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        from .evidence import utc_now

        record = ApprovalRecord(
            request_id=request_id,
            actor=actor,
            role=role,
            action=action,
            reason=reason,
            timestamp=utc_now(),
            evidence_version=evidence_version,
            decision=decision,
            previous_state="PENDING_APPROVAL",
            new_state=decision,
            tenant_id=tenant_id,
        )
        self._approvals.append(record)
        self.audit.append(
            make_event(
                tenant_id=tenant_id,
                actor=actor,
                agent="quantum-commander",
                action=f"approval_{decision}",
                payload={"request_id": request_id, "action": action},
                previous_state="PENDING_APPROVAL",
                new_state=decision,
                decision=decision,
                confidence=1.0,
                approval_reference=request_id,
            )
        )
        return record

    def record_hypothesis(self, tenant_id: str, claim: str, actor: str) -> dict:
        item = hypothesis_item(tenant_id=require_tenant(tenant_id), claim=claim, actor=actor)
        metrics.inc("qics_unverified_claims_total")
        return item.to_dict()
