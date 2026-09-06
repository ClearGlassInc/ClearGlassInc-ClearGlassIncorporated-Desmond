# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass RFED(TM) — Recorded Factual Evidence of Decision.

Deterministic audit-trail core for agentic workflows. Every model-influenced
action is recorded as a four-segment RFED record:

    R — Request    what was asked, by whom, under which policy version
    F — Facts      the grounded inputs the model was actually given
    E — Evidence   model identity, parameters, raw output, output digest
    D — Decision   risk score, tier, route (auto / queued / blocked), approver

Records are linked into a SHA-256 hash chain, so altering any historical entry
invalidates every entry after it. That chain is the "logged evidence of model
accountability": it proves *which* model saw *which* facts and *who* approved
the result.

This module is intentionally dependency-free (stdlib only) so the orchestration
layer (n8n / Cursor agents / CI) can call it without a database or web stack.
No network calls live here; side-effectful adapters belong in the deployment
layer (`deployment/rfed/`).

Risk routing mirrors `clearglass-commerce/control-plane/app/governance.py`:
read-only analysis auto-executes, reversible changes queue for review, and
anything touching access, credentials, remote execution, or the ledger itself
is hard-gated behind a human approval. Unknown actions fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "output" / "rfed"

#: Bumped whenever the risk table or gating logic changes. Recorded on every
#: entry so an auditor can replay a decision against the policy of the day.
POLICY_VERSION = "rfed-1.0.0"

#: First link of the chain. 64 zeroes = "no predecessor".
GENESIS_HASH = "0" * 64


# ---------------------------------------------------------------------------
# Risk model
# ---------------------------------------------------------------------------


class RiskTier(str, Enum):
    """Coarse risk classification that maps to an execution policy."""

    LOW = "low"            # auto-execute + log
    MEDIUM = "medium"      # queue for review
    HIGH = "high"          # approval required
    CRITICAL = "critical"  # approval required, highest scrutiny


class Route(str, Enum):
    """What the governor decided to do with the proposed action."""

    AUTO_EXECUTED = "auto_executed"
    QUEUED_FOR_APPROVAL = "queued_for_approval"
    BLOCKED = "blocked"


# Actions an agentic workflow can propose, mapped to a base risk score (0-100).
ACTION_RISK: dict[str, int] = {
    # low — read-only analysis, fully reversible, no external side effect
    "retrieve_context": 0,
    "read_telemetry": 0,
    "classify_record": 5,
    "summarize_document": 5,
    "score_record": 10,
    "draft_internal_note": 15,
    # medium — reversible but visible to a client or a system of record
    "enrich_record": 30,
    "update_internal_doc": 35,
    "create_ticket": 38,
    "draft_client_comms": 40,
    "publish_report": 45,
    # high — external effect, hard to reverse
    "send_client_comms": 70,
    "close_ticket": 62,
    "push_config_change": 78,
    "quarantine_endpoint": 75,
    # critical — identity, credentials, remote execution, or the ledger itself
    "modify_access_policy": 92,
    "grant_privileged_access": 100,
    "rotate_credentials": 95,
    "execute_remote_command": 98,
    "disable_security_control": 100,
    "export_client_data": 94,
    "modify_audit_log": 100,
}

# Always-escalate triggers, independent of score. These are the actions an
# RMM/zero-trust compromise would reach for first, so they never auto-execute.
ALWAYS_ESCALATE = {
    "modify_access_policy",
    "grant_privileged_access",
    "rotate_credentials",
    "execute_remote_command",
    "disable_security_control",
    "export_client_data",
    "modify_audit_log",
    "push_config_change",
    "quarantine_endpoint",
    "send_client_comms",
}

#: Actions that may never execute from an automated path, approved or not.
#: The ledger is append-only by construction; a workflow that asks to rewrite it
#: is either broken or hostile.
NEVER_AUTOMATE = {"modify_audit_log"}

#: Heuristic markers of prompt injection arriving through retrieved facts.
INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "you are now",
    "system prompt",
    "reveal your instructions",
    "exfiltrate",
    "send credentials",
)

#: Values that must never land in the ledger in the clear.
_REDACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("[redacted:email]", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("[redacted:card]", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
    ("[redacted:sin]", re.compile(r"\b\d{3}[- ]\d{3}[- ]\d{3}\b")),
    ("[redacted:bearer]", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{12,}")),
    ("[redacted:key]", re.compile(r"(?i)\b(?:sk|pk|api|token)[_-][A-Za-z0-9]{16,}")),
)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def utc_now() -> str:
    """ISO-8601 UTC timestamp with a trailing Z, stable across platforms."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(payload: object) -> str:
    """Deterministic JSON encoding — the only form we ever hash.

    Key order, separators, and non-ASCII escaping are all pinned so that the
    same logical record always produces the same digest on any machine.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest(payload: object) -> str:
    """SHA-256 of a payload's canonical form. Used for content without storing it."""
    return sha256_hex(canonical_json(payload))


def redact(value: str) -> str:
    """Strip credentials and direct identifiers before anything is persisted."""
    out = value
    for replacement, pattern in _REDACTION_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def looks_like_injection(text: str) -> list[str]:
    """Return the injection markers present in retrieved text, if any."""
    lowered = text.lower()
    return [marker for marker in INJECTION_MARKERS if marker in lowered]


# ---------------------------------------------------------------------------
# RFED segments
# ---------------------------------------------------------------------------


@dataclass
class Request:
    """R — what was asked, and by whom."""

    actor: str                    # 'n8n:rfed-audit-trail', 'cursor:agent', or a human email
    workflow: str                 # 'client_zero_trust', 'rfed_audit_trail', ...
    action: str                   # key into ACTION_RISK
    target: str                   # endpoint id, ticket id, client slug, ...
    intent: str = ""              # one-line natural-language statement of purpose
    correlation_id: str = ""      # ties multi-step runs together
    input_digest: str = ""        # sha256 of the raw inbound payload

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class Fact:
    """A single grounded input the model was given."""

    source: str                   # 'supabase:tickets', 'nvd:CVE-2026-18577', 'client_doc:policy'
    reference: str                # row id, URL, file path
    content_digest: str           # sha256 of the retrieved content
    retrieved_at: str = field(default_factory=utc_now)
    trusted: bool = True          # False for anything user- or internet-supplied

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class Evidence:
    """E — what the model was and what it produced."""

    model_id: str                 # exact model identifier, never a marketing name
    provider: str = "anthropic"
    temperature: float = 0.0
    max_tokens: int = 0
    prompt_digest: str = ""       # sha256 of the fully-rendered prompt
    output_digest: str = ""       # sha256 of the raw model output
    output_excerpt: str = ""      # redacted, truncated — for human review
    confidence: float = 1.0       # 0.0-1.0 as self-reported or scored upstream
    citations: list[str] = field(default_factory=list)  # Fact.reference values used
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class Decision:
    """D — how the governor routed the action, and who signed it off."""

    score: int
    tier: RiskTier
    route: Route
    requires_approval: bool
    reasons: list[str] = field(default_factory=list)
    approved_by: str | None = None
    approved_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        out = asdict(self)
        out["tier"] = self.tier.value
        out["route"] = self.route.value
        return out


@dataclass
class RfedRecord:
    """One tamper-evident entry in the RFED ledger."""

    request: Request
    facts: list[Fact]
    evidence: Evidence
    decision: Decision
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: str = field(default_factory=utc_now)
    policy_version: str = POLICY_VERSION
    prev_hash: str = GENESIS_HASH
    chain_hash: str = ""

    def body(self) -> dict[str, object]:
        """The hashed portion of the record — everything except `chain_hash`."""
        return {
            "record_id": self.record_id,
            "occurred_at": self.occurred_at,
            "policy_version": self.policy_version,
            "prev_hash": self.prev_hash,
            "request": self.request.to_dict(),
            "facts": [f.to_dict() for f in self.facts],
            "evidence": self.evidence.to_dict(),
            "decision": self.decision.to_dict(),
        }

    def compute_hash(self) -> str:
        """Link this record to its predecessor: sha256(prev_hash || body)."""
        return sha256_hex(self.prev_hash + canonical_json(self.body()))

    def seal(self) -> RfedRecord:
        """Fix the chain hash. Call once, after `prev_hash` is known."""
        self.chain_hash = self.compute_hash()
        return self

    def to_dict(self) -> dict[str, object]:
        out = self.body()
        out["chain_hash"] = self.chain_hash
        return out

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


# ---------------------------------------------------------------------------
# Governor
# ---------------------------------------------------------------------------


def _tier_for_score(score: int) -> RiskTier:
    if score >= 90:
        return RiskTier.CRITICAL
    if score >= 60:
        return RiskTier.HIGH
    if score >= 30:
        return RiskTier.MEDIUM
    return RiskTier.LOW


def assess(
    action: str,
    facts: Sequence[Fact],
    evidence: Evidence,
    *,
    payload: dict[str, object] | None = None,
    low_confidence_threshold: float = 0.75,
) -> Decision:
    """Score a proposed action 0-100 and decide how it is routed.

    Beyond the base action risk, three accountability signals can hard-gate an
    action on their own — a score bump alone is not enough, because a low-base
    action could still land under the HIGH threshold and auto-execute:

    1. **Ungrounded output** — the model cited nothing. Nothing to audit against.
    2. **Low confidence** — below `low_confidence_threshold`.
    3. **Untrusted facts carrying injection markers** — the context is hostile.

    Unknown actions default to HIGH and are gated. Fail closed, never open.
    """
    payload = payload or {}
    reasons: list[str] = []

    base = ACTION_RISK.get(action)
    if base is None:
        reasons.append(f"unknown action '{action}' — defaulting to high risk (fail closed)")
        base = 85
    score = base

    # --- payload signals that raise risk -----------------------------------
    if payload.get("scope") == "all" or payload.get("bulk") is True:
        score = min(100, score + 8)
        reasons.append("affects all managed assets / bulk operation")
    if payload.get("outside_change_window") is True:
        score = min(100, score + 6)
        reasons.append("executes outside the agreed change window")

    # --- accountability signals --------------------------------------------
    ungrounded = not evidence.citations
    if ungrounded:
        score = min(100, score + 15)
        reasons.append("model cited no facts — output is ungrounded and cannot be audited")

    low_confidence = evidence.confidence < low_confidence_threshold
    if low_confidence:
        score = min(100, score + 12)
        reasons.append(
            f"model confidence {evidence.confidence:.2f} below threshold "
            f"{low_confidence_threshold:.2f}"
        )

    tainted: list[str] = []
    for fact in facts:
        if fact.trusted:
            continue
        markers = looks_like_injection(f"{fact.source} {fact.reference}")
        if markers:
            tainted.append(f"{fact.source}:{markers[0]}")
    if tainted:
        score = min(100, score + 20)
        reasons.append(f"possible prompt injection in untrusted facts: {', '.join(tainted)}")

    # Citations must resolve to facts actually supplied to the model. A model
    # citing a reference that was never retrieved is fabricating provenance.
    known_refs = {f.reference for f in facts}
    dangling = [c for c in evidence.citations if c not in known_refs]
    if dangling:
        score = min(100, score + 25)
        reasons.append(f"citations not present in supplied facts: {', '.join(sorted(dangling))}")

    tier = _tier_for_score(score)

    requires_approval = (
        tier in (RiskTier.HIGH, RiskTier.CRITICAL)
        or action in ALWAYS_ESCALATE
        or ungrounded
        or low_confidence
        or bool(tainted)
        or bool(dangling)
    )
    if action in ALWAYS_ESCALATE:
        reasons.append("action is in the always-escalate set (access / credentials / outbound)")

    if action in NEVER_AUTOMATE:
        route = Route.BLOCKED
        reasons.append("action is never automatable — ledger integrity is non-negotiable")
    elif requires_approval:
        route = Route.QUEUED_FOR_APPROVAL
        reasons.append("hard gate enabled — cannot auto-execute")
    else:
        route = Route.AUTO_EXECUTED
        reasons.append("auto-executable: reversible, grounded, low risk")

    return Decision(
        score=score,
        tier=tier,
        route=route,
        requires_approval=requires_approval or route is Route.BLOCKED,
        reasons=reasons,
    )


def build_record(
    request: Request,
    facts: Sequence[Fact],
    evidence: Evidence,
    *,
    prev_hash: str = GENESIS_HASH,
    payload: dict[str, object] | None = None,
) -> RfedRecord:
    """Assess an action and return a sealed, chain-linked RFED record."""
    decision = assess(request.action, facts, evidence, payload=payload)
    evidence.output_excerpt = redact(evidence.output_excerpt)[:500]
    record = RfedRecord(
        request=request,
        facts=list(facts),
        evidence=evidence,
        decision=decision,
        prev_hash=prev_hash,
    )
    return record.seal()


def approve(record: RfedRecord, approver: str, *, at: str | None = None) -> RfedRecord:
    """Record a human approval as a **new** ledger entry.

    The original record is never mutated — that is the whole point of an
    append-only ledger. The returned record carries the approval and links to
    the decision it authorises.
    """
    if record.decision.route is Route.BLOCKED:
        raise ValueError(f"record {record.record_id} is blocked and cannot be approved")
    if not record.decision.requires_approval:
        raise ValueError(f"record {record.record_id} did not require approval")
    if not approver:
        raise ValueError("approver is required")

    approved_decision = Decision(
        score=record.decision.score,
        tier=record.decision.tier,
        route=Route.AUTO_EXECUTED,
        requires_approval=True,
        reasons=[*record.decision.reasons, f"approved by {approver}"],
        approved_by=approver,
        approved_at=at or utc_now(),
    )
    follow_on = RfedRecord(
        request=Request(
            actor=approver,
            workflow=record.request.workflow,
            action=record.request.action,
            target=record.request.target,
            intent=f"human approval of {record.record_id}",
            correlation_id=record.request.correlation_id or record.record_id,
            input_digest=record.chain_hash,
        ),
        facts=list(record.facts),
        evidence=record.evidence,
        decision=approved_decision,
        prev_hash=record.chain_hash,
    )
    return follow_on.seal()


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


@dataclass
class ChainVerification:
    """Outcome of replaying a ledger's hash chain."""

    valid: bool
    checked: int
    broken_at: int | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RfedLedger:
    """Append-only, hash-chained collection of RFED records.

    Backed by JSON Lines on disk so it can be diffed, shipped to a SIEM, or
    replayed by an auditor with nothing but `sha256sum` and patience.
    """

    def __init__(self, records: Iterable[RfedRecord] | None = None) -> None:
        self._records: list[RfedRecord] = list(records or [])

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[RfedRecord]:
        return iter(self._records)

    @property
    def head(self) -> str:
        """Hash of the most recent record — the `prev_hash` for the next append."""
        return self._records[-1].chain_hash if self._records else GENESIS_HASH

    def append(
        self,
        request: Request,
        facts: Sequence[Fact],
        evidence: Evidence,
        *,
        payload: dict[str, object] | None = None,
    ) -> RfedRecord:
        record = build_record(request, facts, evidence, prev_hash=self.head, payload=payload)
        self._records.append(record)
        return record

    def append_record(self, record: RfedRecord) -> RfedRecord:
        """Append an already-built record, re-linking it to the current head."""
        if record.prev_hash != self.head:
            record.prev_hash = self.head
            record.seal()
        self._records.append(record)
        return record

    def verify(self) -> ChainVerification:
        """Replay the chain. Any edit to any record breaks every link after it."""
        expected_prev = GENESIS_HASH
        for index, record in enumerate(self._records):
            if record.prev_hash != expected_prev:
                return ChainVerification(
                    valid=False,
                    checked=index,
                    broken_at=index,
                    reason=(
                        f"record {record.record_id} expected prev_hash {expected_prev[:12]}… "
                        f"but carries {record.prev_hash[:12]}…"
                    ),
                )
            recomputed = record.compute_hash()
            if recomputed != record.chain_hash:
                return ChainVerification(
                    valid=False,
                    checked=index,
                    broken_at=index,
                    reason=(
                        f"record {record.record_id} content does not match its seal "
                        f"(recomputed {recomputed[:12]}…, stored {record.chain_hash[:12]}…)"
                    ),
                )
            expected_prev = record.chain_hash
        return ChainVerification(valid=True, checked=len(self._records), reason="chain intact")

    # --- persistence -------------------------------------------------------

    def to_jsonl(self) -> str:
        return "\n".join(record.to_json() for record in self._records)

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_jsonl()
        path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
        return path

    @classmethod
    def from_jsonl(cls, text: str) -> RfedLedger:
        records = [_record_from_dict(json.loads(line)) for line in text.splitlines() if line.strip()]
        return cls(records)

    @classmethod
    def read(cls, path: Path) -> RfedLedger:
        return cls.from_jsonl(path.read_text(encoding="utf-8"))


def _record_from_dict(data: dict[str, object]) -> RfedRecord:
    """Rehydrate a record from its serialized form without re-sealing it.

    Deliberately preserves the stored `chain_hash` so that `verify()` can catch
    a tampered ledger instead of silently repairing it.
    """
    decision_raw = dict(data["decision"])  # type: ignore[arg-type]
    decision = Decision(
        score=int(decision_raw["score"]),
        tier=RiskTier(decision_raw["tier"]),
        route=Route(decision_raw["route"]),
        requires_approval=bool(decision_raw["requires_approval"]),
        reasons=list(decision_raw.get("reasons", [])),
        approved_by=decision_raw.get("approved_by"),
        approved_at=decision_raw.get("approved_at"),
    )
    return RfedRecord(
        request=Request(**data["request"]),      # type: ignore[arg-type]
        facts=[Fact(**f) for f in data["facts"]],  # type: ignore[union-attr]
        evidence=Evidence(**data["evidence"]),   # type: ignore[arg-type]
        decision=decision,
        record_id=str(data["record_id"]),
        occurred_at=str(data["occurred_at"]),
        policy_version=str(data["policy_version"]),
        prev_hash=str(data["prev_hash"]),
        chain_hash=str(data.get("chain_hash", "")),
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def accountability_summary(ledger: RfedLedger) -> dict[str, object]:
    """Roll a ledger up into the evidence pack an auditor or client asks for."""
    verification = ledger.verify()
    by_route: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    models: dict[str, int] = {}
    ungrounded = 0
    approvals = 0

    for record in ledger:
        by_route[record.decision.route.value] = by_route.get(record.decision.route.value, 0) + 1
        by_tier[record.decision.tier.value] = by_tier.get(record.decision.tier.value, 0) + 1
        models[record.evidence.model_id] = models.get(record.evidence.model_id, 0) + 1
        if not record.evidence.citations:
            ungrounded += 1
        if record.decision.approved_by:
            approvals += 1

    return {
        "generated_at": utc_now(),
        "policy_version": POLICY_VERSION,
        "records": len(ledger),
        "chain": verification.to_dict(),
        "head": ledger.head,
        "by_route": by_route,
        "by_tier": by_tier,
        "models_used": models,
        "ungrounded_outputs": ungrounded,
        "human_approvals": approvals,
    }


def render_summary(summary: dict[str, object]) -> str:
    """Human-readable brief, matching the house report style."""
    chain = summary["chain"]
    status = "INTACT" if chain["valid"] else f"BROKEN at #{chain['broken_at']}"  # type: ignore[index]
    lines = [
        "# RFED(TM) Accountability Summary",
        "",
        f"- Generated: {summary['generated_at']}",
        f"- Policy: {summary['policy_version']}",
        f"- Records: {summary['records']}",
        f"- Chain: **{status}** — {chain['reason']}",  # type: ignore[index]
        f"- Head: `{summary['head']}`",
        "",
        "## Routing",
    ]
    for route, count in sorted(summary["by_route"].items()):  # type: ignore[union-attr]
        lines.append(f"- {route}: {count}")
    lines += ["", "## Risk tiers"]
    for tier, count in sorted(summary["by_tier"].items()):  # type: ignore[union-attr]
        lines.append(f"- {tier}: {count}")
    lines += ["", "## Models"]
    for model, count in sorted(summary["models_used"].items()):  # type: ignore[union-attr]
        lines.append(f"- `{model}`: {count} decision(s)")
    lines += [
        "",
        f"Ungrounded outputs (gated): {summary['ungrounded_outputs']}",
        f"Human approvals recorded: {summary['human_approvals']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-check + CLI
# ---------------------------------------------------------------------------


def self_check() -> tuple[RfedLedger, list[str]]:
    """Exercise the governor end-to-end and assert the invariants hold.

    Run by `Commerce Daily Loop`-style CI to prove the gate still gates.
    Returns the demo ledger and a list of failures (empty == healthy).
    """
    failures: list[str] = []
    ledger = RfedLedger()

    fact = Fact(
        source="supabase:endpoints",
        reference="endpoint/BRL-014",
        content_digest=digest({"host": "BRL-014", "patch_level": "2026.3.1"}),
    )
    grounded = Evidence(
        model_id="claude-opus-5",
        temperature=0.0,
        max_tokens=1024,
        prompt_digest=digest("assess patch level"),
        output_digest=digest("BRL-014 is behind on N-central hotfix"),
        output_excerpt="BRL-014 is running 2026.3.1 without Hotfix 1.",
        confidence=0.94,
        citations=["endpoint/BRL-014"],
    )

    # 1. A grounded read-only action auto-executes.
    low = ledger.append(
        Request(
            actor="n8n:rfed-audit-trail",
            workflow="client_zero_trust",
            action="read_telemetry",
            target="endpoint/BRL-014",
            intent="check RMM agent patch level",
        ),
        [fact],
        grounded,
    )
    if low.decision.route is not Route.AUTO_EXECUTED:
        failures.append(f"read_telemetry should auto-execute, got {low.decision.route.value}")

    # 2. A privileged action is gated even with perfect grounding.
    high = ledger.append(
        Request(
            actor="n8n:rfed-audit-trail",
            workflow="client_zero_trust",
            action="execute_remote_command",
            target="endpoint/BRL-014",
            intent="apply N-central hotfix",
        ),
        [fact],
        grounded,
    )
    if not high.decision.requires_approval:
        failures.append("execute_remote_command must require approval")
    if high.decision.tier is not RiskTier.CRITICAL:
        failures.append(f"execute_remote_command should be critical, got {high.decision.tier.value}")

    # 3. An ungrounded low-risk action is gated on the accountability signal alone.
    ungrounded = ledger.append(
        Request(
            actor="n8n:rfed-audit-trail",
            workflow="client_zero_trust",
            action="classify_record",
            target="ticket/9182",
            intent="classify inbound ticket",
        ),
        [fact],
        Evidence(model_id="claude-opus-5", confidence=0.99, citations=[]),
    )
    if not ungrounded.decision.requires_approval:
        failures.append("ungrounded output must be gated even at low base risk")

    # 4. Ledger rewrites are blocked outright.
    blocked = ledger.append(
        Request(
            actor="n8n:rfed-audit-trail",
            workflow="rfed_audit_trail",
            action="modify_audit_log",
            target="ledger",
            intent="compact old entries",
        ),
        [fact],
        grounded,
    )
    if blocked.decision.route is not Route.BLOCKED:
        failures.append("modify_audit_log must be blocked outright")

    # 5. Unknown actions fail closed.
    unknown = ledger.append(
        Request(
            actor="n8n:rfed-audit-trail",
            workflow="client_zero_trust",
            action="wire_transfer",
            target="acct/0001",
            intent="unmapped action",
        ),
        [fact],
        grounded,
    )
    if not unknown.decision.requires_approval:
        failures.append("unknown action must fail closed")

    # 6. Approval appends a new record and preserves the chain.
    approval = approve(high, "desmond@clearglassinc.com")
    ledger.append_record(approval)
    if approval.decision.approved_by != "desmond@clearglassinc.com":
        failures.append("approval must record the approver")

    # 7. The chain verifies.
    verification = ledger.verify()
    if not verification.valid:
        failures.append(f"chain should verify: {verification.reason}")

    # 8. Tampering is detected.
    probe = RfedLedger.from_jsonl(ledger.to_jsonl())
    list(probe)[1].request.target = "endpoint/OTHER"
    if probe.verify().valid:
        failures.append("tampered ledger must fail verification")

    return ledger, failures


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rfed_audit_bot",
        description="ClearGlass RFED(TM) audit-trail governor and ledger verifier.",
    )
    parser.add_argument("--verify", metavar="LEDGER", help="verify a JSONL ledger's hash chain")
    parser.add_argument("--summary", metavar="LEDGER", help="print an accountability summary")
    parser.add_argument("--self-check", action="store_true", help="run governance invariants")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--write", action="store_true", help="write outputs to operations/output/rfed")
    args = parser.parse_args(argv)

    if args.verify:
        ledger = RfedLedger.read(Path(args.verify))
        result = ledger.verify()
        if args.json:
            print(canonical_json(result.to_dict()))
        else:
            state = "INTACT" if result.valid else "BROKEN"
            print(f"chain {state}: {result.reason} ({result.checked} record(s) checked)")
        return 0 if result.valid else 1

    if args.summary:
        ledger = RfedLedger.read(Path(args.summary))
        summary = accountability_summary(ledger)
        print(canonical_json(summary) if args.json else render_summary(summary))
        return 0 if summary["chain"]["valid"] else 1  # type: ignore[index]

    if args.self_check:
        ledger, failures = self_check()
        summary = accountability_summary(ledger)
        if args.write:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            ledger.write(OUTPUT_DIR / "self_check_ledger.jsonl")
            (OUTPUT_DIR / "self_check_summary.json").write_text(
                canonical_json(summary) + "\n", encoding="utf-8"
            )
            (OUTPUT_DIR / "self_check_summary.md").write_text(
                render_summary(summary) + "\n", encoding="utf-8"
            )
        if args.json:
            print(canonical_json({"failures": failures, "summary": summary}))
        else:
            print(render_summary(summary))
            print()
            if failures:
                print(f"SELF-CHECK FAILED ({len(failures)}):")
                for failure in failures:
                    print(f"  - {failure}")
            else:
                print("SELF-CHECK PASSED — governance invariants hold.")
        return 1 if failures else 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
