"""In-process append-only audit log. Records are never updated or deleted."""

from __future__ import annotations

from .evidence import content_hash, utc_now
from .schema import AuditEvent


class AppendOnlyAudit:
    def __init__(self) -> None:
        self._rows: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        self._rows.append(event)
        return event

    def update(self, *_a, **_k) -> None:  # noqa: ANN002
        raise RuntimeError("audit log is append-only")

    def delete(self, *_a, **_k) -> None:  # noqa: ANN002
        raise RuntimeError("audit log is append-only")

    def list_for_tenant(self, tenant_id: str) -> list[AuditEvent]:
        return [e for e in self._rows if e.tenant_id == tenant_id]

    @property
    def rows(self) -> tuple[AuditEvent, ...]:
        return tuple(self._rows)


def make_event(
    *,
    tenant_id: str,
    actor: str,
    agent: str,
    action: str,
    payload: dict,
    previous_state: str,
    new_state: str,
    decision: str,
    confidence: float,
    approval_reference: str | None = None,
) -> AuditEvent:
    body_hash = content_hash(payload)
    return AuditEvent(
        event_id=body_hash[7:23],
        timestamp=utc_now(),
        tenant_id=tenant_id,
        actor=actor,
        agent=agent,
        action=action,
        input_hash=body_hash,
        evidence_hash=content_hash({"action": action, "state": new_state}),
        previous_state=previous_state,
        new_state=new_state,
        decision=decision,
        confidence=confidence,
        approval_reference=approval_reference,
    )
