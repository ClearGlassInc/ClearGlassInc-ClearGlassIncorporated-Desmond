# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Percival mission memory — a real, persistent, governed operator model.

This is the durable "operator model" the Percival system prompt refers to: a
JSON-backed store of goals, projects, constraints, preferences, risks,
deadlines, stakeholders, technical context, business priorities, and brand
position that survives across sessions so the executive layer can reconstruct
context instead of starting cold.

Governance invariants (mirroring the ClearGlass safety model):

  * **No fabrication.** The store only ever holds what was explicitly handed to
    it. Every item carries provenance (`source`) and a `confidence` of either
    ``stated`` (the operator said it) or ``inferred`` (Percival's working
    assumption) — inferred items must never be surfaced as fact.
  * **Auditable.** Every mutation is written to an append-only, hash-chained
    ledger (:class:`sentinel.audit.AuditLog`), so history is tamper-evident.
  * **Approval-gated.** Reads and remembering context are free; deriving a
    sensitive, irreversible, or money-moving *action* from memory is gated by
    :func:`requires_approval`, which fails closed.

Stdlib only, so it runs in minimal CI environments alongside the other governed
modules.
"""
from __future__ import annotations

import datetime as _dt
import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from .audit import AuditLog

# The persistent operator model — the dimensions Percival tracks about the
# operator and the business across sessions.
SECTIONS = frozenset(
    {
        "goals",
        "projects",
        "constraints",
        "preferences",
        "risks",
        "deadlines",
        "stakeholders",
        "technical_context",
        "business_priorities",
        "brand_position",
        "dependencies",          # what must land before what (mission graph edges)
        "approval_boundaries",   # standing thresholds for what needs human sign-off
        "approved_workflows",    # workflows the operator has blessed for reuse
        "decision_history",      # prior decisions, for continuity and non-repetition
    }
)

# Confidence levels. `stated` = the operator asserted it; `inferred` = Percival's
# labeled working assumption. Anything inferred must stay labeled as such.
CONFIDENCE = frozenset({"stated", "inferred"})

# Action kinds that must never execute off remembered context without an
# explicit human approval (fail-closed governance).
_SENSITIVE_ACTION_KINDS = frozenset(
    {
        "money_movement",
        "pricing_change",
        "payment",
        "refund",
        "fulfillment",
        "production_change",
        "external_send",
        "destructive",
        "credential_access",
    }
)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def requires_approval(action_kind: str, *, technical_risk: int = 0) -> bool:
    """Fail-closed gate for actions derived from memory.

    Returns True (approval required) for any sensitive action kind, for any
    unrecognised kind, or when the estimated technical risk is non-trivial.
    Only explicitly-safe, low-risk, reversible kinds pass without approval.
    """
    if action_kind in _SENSITIVE_ACTION_KINDS:
        return True
    if technical_risk > 2:
        return True
    # Fail closed: only a short safe-list of read/draft kinds auto-pass.
    return action_kind not in {"read", "summarize", "draft", "analyze", "recall"}


@dataclass
class MemoryItem:
    """A single remembered fact, always carrying its provenance."""

    id: str
    section: str
    content: str
    source: str                       # provenance — who/what supplied this
    confidence: str                   # "stated" | "inferred"
    ts: str
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Feedback:
    """A rating on a prior output, used to adapt future depth/style."""

    ts: str
    task: str
    rating: int                       # -2 (bad) .. +2 (excellent)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MissionMemory:
    """Persistent, governed operator model for Percival.

    Parameters
    ----------
    path:
        JSON file backing the store. If it exists it is loaded on construction.
        If ``None`` the store is purely in-memory (useful for tests / ephemeral
        sessions).
    audit:
        An :class:`AuditLog` to record mutations into. One is created if omitted.
    """

    def __init__(self, path: Optional[Path | str] = None, *, audit: Optional[AuditLog] = None) -> None:
        self.path = Path(path) if path else None
        self.audit = audit or AuditLog()
        self._items: dict[str, MemoryItem] = {}
        self._feedback: list[Feedback] = []
        if self.path and self.path.exists():
            self._load()

    # ------------------------------------------------------------------ #
    # Remember / forget (governed, provenance-required)
    # ------------------------------------------------------------------ #
    def remember(
        self,
        section: str,
        content: str,
        *,
        source: str,
        confidence: str = "stated",
        tags: Optional[list[str]] = None,
        actor: str = "percival",
    ) -> MemoryItem:
        """Store a fact. `source` (provenance) is mandatory — nothing is stored
        without knowing where it came from, so the model can never fabricate."""
        if section not in SECTIONS:
            raise ValueError(f"unknown section {section!r}; valid: {sorted(SECTIONS)}")
        if confidence not in CONFIDENCE:
            raise ValueError(f"confidence must be one of {sorted(CONFIDENCE)}")
        if not source or not source.strip():
            raise ValueError("source (provenance) is required — refusing to store an unsourced fact")
        if not content or not content.strip():
            raise ValueError("content is required")

        item = MemoryItem(
            id=uuid.uuid4().hex,
            section=section,
            content=content.strip(),
            source=source.strip(),
            confidence=confidence,
            ts=_now(),
            tags=list(tags or []),
        )
        self._items[item.id] = item
        self.audit.record(
            actor=actor,
            action="remember",
            detail={"id": item.id, "section": section, "confidence": confidence, "source": item.source},
        )
        self._save()
        return item

    def forget(self, item_id: str, *, actor: str = "percival") -> bool:
        """Remove a remembered fact. Audited. Returns False if it was absent."""
        item = self._items.pop(item_id, None)
        if item is None:
            return False
        self.audit.record(actor=actor, action="forget", detail={"id": item_id, "section": item.section})
        self._save()
        return True

    # ------------------------------------------------------------------ #
    # Feedback loop (continuous learning from ratings)
    # ------------------------------------------------------------------ #
    def record_feedback(self, task: str, rating: int, note: str = "", *, actor: str = "operator") -> Feedback:
        """Record a rating on a prior output so future outputs can adapt."""
        rating = max(-2, min(2, int(rating)))
        fb = Feedback(ts=_now(), task=task.strip(), rating=rating, note=note.strip())
        self._feedback.append(fb)
        self.audit.record(actor=actor, action="feedback", detail={"task": fb.task, "rating": rating})
        self._save()
        return fb

    def preferred_depth(self) -> str:
        """Adapt output depth from feedback: consistently-positive ratings on
        concise work bias toward `concise`; negative ratings bias toward
        `thorough`. Neutral by default."""
        if not self._feedback:
            return "balanced"
        avg = sum(f.rating for f in self._feedback) / len(self._feedback)
        if avg >= 1:
            return "concise"
        if avg <= -1:
            return "thorough"
        return "balanced"

    # ------------------------------------------------------------------ #
    # Reads / context reconstruction
    # ------------------------------------------------------------------ #
    def items(self, section: Optional[str] = None) -> list[MemoryItem]:
        vals = list(self._items.values())
        if section is not None:
            if section not in SECTIONS:
                raise ValueError(f"unknown section {section!r}")
            vals = [i for i in vals if i.section == section]
        return sorted(vals, key=lambda i: i.ts)

    def reconstruct(self) -> dict[str, Any]:
        """Rebuild the operator model as a structured briefing for a new session."""
        model: dict[str, list[dict[str, Any]]] = {s: [] for s in sorted(SECTIONS)}
        for item in self.items():
            model[item.section].append(item.as_dict())
        return {
            "generated_utc": _now(),
            "operator_model": model,
            "counts": {s: len(v) for s, v in model.items() if v},
            "preferred_depth": self.preferred_depth(),
            "audit_ok": self.verify(),
            "total_items": len(self._items),
        }

    def briefing(self) -> str:
        """Human-readable session-start briefing. `inferred` items are labeled so
        they are never mistaken for stated fact."""
        lines = ["# Percival Mission Briefing", "", f"_Reconstructed {_now()}_", ""]
        any_content = False
        for section in sorted(SECTIONS):
            items = self.items(section)
            if not items:
                continue
            any_content = True
            lines.append(f"## {section.replace('_', ' ').title()}")
            for i in items:
                tag = "" if i.confidence == "stated" else " _(inferred — unverified)_"
                lines.append(f"- {i.content}{tag}  \n  ↳ source: {i.source}")
            lines.append("")
        if not any_content:
            lines.append("_No mission memory yet. Nothing remembered — will not fabricate._")
        lines.append(f"\n**Preferred output depth:** {self.preferred_depth()}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Persistence + integrity
    # ------------------------------------------------------------------ #
    def verify(self) -> bool:
        """True if the audit chain is intact (tamper-evident)."""
        return self.audit.verify()

    def _serialize(self) -> dict[str, Any]:
        return {
            "version": 1,
            "items": [i.as_dict() for i in self._items.values()],
            "feedback": [f.as_dict() for f in self._feedback],
        }

    def _save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._serialize(), indent=2))
        tmp.replace(self.path)  # atomic on POSIX

    def _load(self) -> None:
        assert self.path is not None
        raw = json.loads(self.path.read_text())
        for d in raw.get("items", []):
            item = MemoryItem(
                id=d["id"],
                section=d["section"],
                content=d["content"],
                source=d["source"],
                confidence=d.get("confidence", "stated"),
                ts=d["ts"],
                tags=list(d.get("tags", [])),
            )
            self._items[item.id] = item
        for d in raw.get("feedback", []):
            self._feedback.append(Feedback(ts=d["ts"], task=d["task"], rating=int(d["rating"]), note=d.get("note", "")))
