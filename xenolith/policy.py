# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH policy engine — the gate every action passes through.

This is the keystone of the lattice's zero-trust model. It is the only place
that answers "may this happen?", and it answers deny-by-default:

* An unknown action class is **denied**, not waved through. Adding a capability
  means adding a rule, which means a reviewed diff.
* Risk is scored 0–100 and mapped onto the shared ``RiskTier`` ladder. ``LOW``
  auto-executes; ``MEDIUM`` queues for approval; ``HIGH``/``CRITICAL`` are
  hard-blocked until an approval is recorded.
* An **approval is bound to the exact action** it was granted for, by digest.
  Approving one pricing change does not approve the next one, and mutating a
  payload after approval invalidates it.
* An approver may not approve their own request. Self-approval is the failure
  mode that makes every other control cosmetic.
* Output is sanitized on the way out — credentials and contact identifiers are
  redacted before anything is rendered, logged or forwarded.

Mirrors ``clearglass-commerce/control-plane/app/governance.py`` so a risk score
carries the same meaning across the ClearGlass estate.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from .constants import Domain, PolicyViolation, RiskTier, canonical


class Decision(str, Enum):
    """What the gate decided."""

    ALLOW = "allow"
    QUEUE_APPROVAL = "queue_approval"
    BLOCK_PENDING_APPROVAL = "block_pending_approval"
    DENY = "deny"

    @property
    def executable(self) -> bool:
        return self is Decision.ALLOW


@dataclass(frozen=True)
class ActionRule:
    """Policy for one class of action.

    ``base_risk`` is the floor; :class:`PolicyEngine` adds situational risk on
    top (blast radius, external reach, irreversibility, agent health).
    """

    action: str
    base_risk: int
    required_permission: str
    domains: frozenset[Domain] = field(default_factory=frozenset)
    irreversible: bool = False
    external_reach: bool = False
    description: str = ""

    def permits_domain(self, domain: Domain) -> bool:
        return not self.domains or domain in self.domains


@dataclass
class ProposedAction:
    """A candidate action awaiting judgement."""

    action: str
    actor: str
    domain: Domain
    payload: Mapping[str, Any] = field(default_factory=dict)
    targets: tuple[str, ...] = ()
    trace_id: str | None = None

    def digest(self) -> str:
        """Content address of this exact action, used to bind approvals."""
        return hashlib.sha256(
            canonical(
                {
                    "action": self.action,
                    "actor": self.actor,
                    "domain": self.domain.value,
                    "payload": dict(self.payload),
                    "targets": list(self.targets),
                }
            )
        ).hexdigest()


@dataclass(frozen=True)
class Verdict:
    """The gate's answer, with the reasoning that produced it."""

    decision: Decision
    risk_score: int
    tier: RiskTier
    reasons: tuple[str, ...]
    action_digest: str
    approval_id: str | None = None

    @property
    def executable(self) -> bool:
        return self.decision.executable

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "risk_score": self.risk_score,
            "tier": self.tier.value,
            "reasons": list(self.reasons),
            "action_digest": self.action_digest,
            "approval_id": self.approval_id,
        }


@dataclass
class ApprovalRequest:
    """A queued human decision, bound to one action digest."""

    approval_id: str
    action_digest: str
    action: str
    requested_by: str
    risk_score: int
    tier: RiskTier
    state: str = "pending"
    decided_by: str | None = None
    decided_at: float | None = None
    note: str = ""
    requested_at: float = field(default_factory=time.time)

    @property
    def approved(self) -> bool:
        return self.state == "approved"

    def as_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "action_digest": self.action_digest,
            "action": self.action,
            "requested_by": self.requested_by,
            "risk_score": self.risk_score,
            "tier": self.tier.value,
            "state": self.state,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "note": self.note,
            "requested_at": self.requested_at,
        }


# --------------------------------------------------------------------------- #
# Output sanitization
# --------------------------------------------------------------------------- #
#: Patterns redacted from any text leaving the lattice. Ordered most-specific
#: first so a bearer token is masked as a token, not as a bare word.
_REDACTIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("BEARER_TOKEN", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{8,}", re.IGNORECASE)),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----.*?-----END[A-Z ]*PRIVATE KEY-----", re.DOTALL)),
    ("API_KEY", re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{8,}\b")),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("SECRET_ASSIGNMENT", re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*\S+")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("IPV4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
)


def sanitize(text: str) -> str:
    """Redact credentials and contact identifiers from outbound text."""
    if not text:
        return text
    for label, pattern in _REDACTIONS:
        text = pattern.sub(f"[REDACTED:{label}]", text)
    return text


def sanitize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively sanitize every string in a nested structure."""

    def _walk(value: Any) -> Any:
        if isinstance(value, str):
            return sanitize(value)
        if isinstance(value, Mapping):
            return {k: _walk(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_walk(v) for v in value]
        return value

    return {k: _walk(v) for k, v in payload.items()}


# --------------------------------------------------------------------------- #
# Baseline rule set
# --------------------------------------------------------------------------- #
def default_rules() -> tuple[ActionRule, ...]:
    """The rules the lattice ships with.

    Read and draft paths are cheap. Anything that reaches outside the lattice,
    changes an identity's authority, or cannot be undone is expensive.
    """
    return (
        ActionRule("intel.read", 5, "intel.read", description="Read fused intelligence"),
        ActionRule("intel.ingest", 10, "intel.ingest", description="Ingest a source observation"),
        ActionRule("intel.correlate", 12, "intel.analyze", description="Correlate observations"),
        ActionRule("intel.publish_packet", 34, "intel.publish", description="Publish an intelligence packet"),
        ActionRule("graph.assert", 15, "graph.write", description="Assert an entity or relationship"),
        ActionRule("graph.retract", 38, "graph.write", description="Retract a prior assertion"),
        ActionRule("telemetry.read", 5, "telemetry.read", description="Read metrics and traces"),
        ActionRule(
            "cyber.contain",
            72,
            "cyber.respond",
            domains=frozenset({Domain.CYBERSECURITY}),
            irreversible=True,
            description="Contain or isolate an asset",
        ),
        ActionRule(
            "cyber.block_indicator",
            58,
            "cyber.respond",
            domains=frozenset({Domain.CYBERSECURITY}),
            external_reach=True,
            description="Push a blocking rule to enforcement points",
        ),
        ActionRule(
            "cyber.forensic_capture",
            30,
            "cyber.forensics",
            domains=frozenset({Domain.CYBERSECURITY}),
            description="Capture forensic evidence with chain of custody",
        ),
        ActionRule(
            "threat.score",
            12,
            "threat.analyze",
            domains=frozenset({Domain.THREAT_INTEL, Domain.INTELLIGENCE}),
            description="Score an adversary signal",
        ),
        ActionRule(
            "threat.watchlist_add",
            40,
            "threat.curate",
            domains=frozenset({Domain.THREAT_INTEL}),
            description="Add an actor or indicator to a watchlist",
        ),
        ActionRule(
            "agent.spawn",
            36,
            "agent.delegate",
            description="Spawn a scoped sub-agent",
        ),
        ActionRule(
            "agent.grant_permission",
            88,
            "agent.administer",
            irreversible=True,
            description="Alter an agent's authority",
        ),
        ActionRule(
            "agent.quarantine",
            45,
            "agent.administer",
            description="Isolate a misbehaving agent",
        ),
        ActionRule(
            "outbound.notify",
            62,
            "outbound.send",
            external_reach=True,
            description="Send a message outside the lattice",
        ),
        ActionRule(
            "executive.commit_mission",
            48,
            "executive.command",
            domains=frozenset({Domain.EXECUTIVE}),
            description="Commit a mission to execution",
        ),
        ActionRule(
            "policy.amend",
            95,
            "policy.administer",
            irreversible=True,
            description="Change the policy rule set itself",
        ),
    )


class PolicyEngine:
    """Deny-by-default gate, approval ledger and output sanitizer."""

    def __init__(
        self,
        rules: Iterable[ActionRule] | None = None,
        registry: Any | None = None,
    ) -> None:
        self._rules: dict[str, ActionRule] = {
            rule.action: rule for rule in (rules if rules is not None else default_rules())
        }
        self._registry = registry
        self._approvals: dict[str, ApprovalRequest] = {}
        self._by_digest: dict[str, str] = {}
        self._counter = 0

    # ------------------------------------------------------------------ #
    # Rules
    # ------------------------------------------------------------------ #
    def rule(self, action: str) -> ActionRule | None:
        return self._rules.get(action)

    @property
    def actions(self) -> tuple[str, ...]:
        return tuple(sorted(self._rules))

    def amend(self, rule: ActionRule, approved_by: str) -> ActionRule:
        """Install or replace a rule. Requires a named human, by construction.

        Changing policy is itself the highest-risk operation in the lattice, so
        it does not go through :meth:`evaluate` — it demands an explicit human
        name at the call site, recorded by the caller in the audit ledger.
        """
        if not approved_by or not approved_by.strip():
            raise PolicyViolation("amending policy requires a named human approver")
        self._rules[rule.action] = rule
        return rule

    # ------------------------------------------------------------------ #
    # Evaluation
    # ------------------------------------------------------------------ #
    def score(self, proposed: ProposedAction) -> tuple[int, tuple[str, ...]]:
        """Compute a 0–100 risk score and the reasons behind it."""
        rule = self._rules.get(proposed.action)
        if rule is None:
            return 100, (f"unknown action class '{proposed.action}' — denied by default",)

        score = rule.base_risk
        reasons = [f"base risk {rule.base_risk} for {rule.action}"]

        if rule.irreversible:
            score += 12
            reasons.append("action is irreversible (+12)")
        if rule.external_reach:
            score += 10
            reasons.append("action reaches outside the lattice (+10)")

        # Blast radius: acting on many targets at once is categorically riskier
        # than acting on one, which is what makes mass-outbound dangerous.
        target_count = len(proposed.targets)
        if target_count > 100:
            score += 20
            reasons.append(f"mass action across {target_count} targets (+20)")
        elif target_count > 10:
            score += 10
            reasons.append(f"broad action across {target_count} targets (+10)")
        elif target_count > 1:
            score += 4
            reasons.append(f"multi-target action ({target_count}) (+4)")

        if self._registry is not None:
            record = self._registry.find(proposed.actor)
            if record is None:
                score += 25
                reasons.append("actor is not in the registry (+25)")
            else:
                if not record.status.can_act:
                    score += 30
                    reasons.append(f"actor status is {record.status.value} (+30)")
                if record.health < 0.5:
                    score += 8
                    reasons.append(f"actor health degraded to {record.health:.2f} (+8)")

        return max(0, min(100, score)), tuple(reasons)

    def evaluate(self, proposed: ProposedAction) -> Verdict:
        """Judge an action. Never executes anything; returns the decision only."""
        digest = proposed.digest()
        rule = self._rules.get(proposed.action)
        score, reasons = self.score(proposed)

        if rule is None:
            return Verdict(
                decision=Decision.DENY,
                risk_score=score,
                tier=RiskTier.CRITICAL,
                reasons=reasons,
                action_digest=digest,
            )

        if not rule.permits_domain(proposed.domain):
            return Verdict(
                decision=Decision.DENY,
                risk_score=100,
                tier=RiskTier.CRITICAL,
                reasons=reasons
                + (
                    f"domain '{proposed.domain.value}' may not perform {rule.action}; "
                    f"permitted: {sorted(d.value for d in rule.domains)}",
                ),
                action_digest=digest,
            )

        if self._registry is not None and not self._registry.has_permission(
            proposed.actor, rule.required_permission
        ):
            return Verdict(
                decision=Decision.DENY,
                risk_score=100,
                tier=RiskTier.CRITICAL,
                reasons=reasons
                + (f"{proposed.actor} lacks required permission '{rule.required_permission}'",),
                action_digest=digest,
            )

        tier = RiskTier.from_score(score)

        # An approval already granted for this exact digest unlocks execution.
        approval = self._approval_for(digest)
        if approval is not None and approval.approved:
            return Verdict(
                decision=Decision.ALLOW,
                risk_score=score,
                tier=tier,
                reasons=reasons + (f"approved by {approval.decided_by}",),
                action_digest=digest,
                approval_id=approval.approval_id,
            )
        if approval is not None and approval.state == "rejected":
            return Verdict(
                decision=Decision.DENY,
                risk_score=score,
                tier=tier,
                reasons=reasons + (f"rejected by {approval.decided_by}",),
                action_digest=digest,
                approval_id=approval.approval_id,
            )

        if not tier.requires_approval:
            return Verdict(
                decision=Decision.ALLOW,
                risk_score=score,
                tier=tier,
                reasons=reasons,
                action_digest=digest,
            )

        pending = approval or self._queue(proposed, digest, score, tier)
        decision = (
            Decision.BLOCK_PENDING_APPROVAL
            if tier.blocks_until_approved
            else Decision.QUEUE_APPROVAL
        )
        return Verdict(
            decision=decision,
            risk_score=score,
            tier=tier,
            reasons=reasons + (f"awaiting approval {pending.approval_id}",),
            action_digest=digest,
            approval_id=pending.approval_id,
        )

    def require(self, proposed: ProposedAction) -> Verdict:
        """Evaluate and raise unless the action may execute right now."""
        verdict = self.evaluate(proposed)
        if not verdict.executable:
            raise PolicyViolation(
                f"{proposed.action} blocked ({verdict.decision.value}, "
                f"risk {verdict.risk_score}/{verdict.tier.value}): {'; '.join(verdict.reasons)}"
            )
        return verdict

    # ------------------------------------------------------------------ #
    # Approvals
    # ------------------------------------------------------------------ #
    def _queue(
        self, proposed: ProposedAction, digest: str, score: int, tier: RiskTier
    ) -> ApprovalRequest:
        self._counter += 1
        approval = ApprovalRequest(
            approval_id=f"apr-{self._counter:05d}",
            action_digest=digest,
            action=proposed.action,
            requested_by=proposed.actor,
            risk_score=score,
            tier=tier,
        )
        self._approvals[approval.approval_id] = approval
        self._by_digest[digest] = approval.approval_id
        return approval

    def _approval_for(self, digest: str) -> ApprovalRequest | None:
        approval_id = self._by_digest.get(digest)
        return self._approvals.get(approval_id) if approval_id else None

    def decide(
        self, approval_id: str, approver: str, approve: bool, note: str = ""
    ) -> ApprovalRequest:
        """Record a human decision on a queued approval."""
        approval = self._approvals.get(approval_id)
        if approval is None:
            raise PolicyViolation(f"unknown approval: {approval_id}")
        if approval.state != "pending":
            raise PolicyViolation(
                f"approval {approval_id} is already {approval.state} and cannot be re-decided"
            )
        if not approver or not approver.strip():
            raise PolicyViolation("approver is required")
        if approver == approval.requested_by:
            raise PolicyViolation(
                f"{approver} may not approve their own request ({approval_id})"
            )
        approval.state = "approved" if approve else "rejected"
        approval.decided_by = approver.strip()
        approval.decided_at = time.time()
        approval.note = note
        return approval

    def approvals(self, state: str | None = None) -> tuple[ApprovalRequest, ...]:
        items = sorted(self._approvals.values(), key=lambda a: a.approval_id)
        if state is None:
            return tuple(items)
        return tuple(a for a in items if a.state == state)

    def pending(self) -> tuple[ApprovalRequest, ...]:
        return self.approvals("pending")

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #
    def snapshot(self) -> dict[str, Any]:
        approvals = self.approvals()
        return {
            "rules": len(self._rules),
            "approvals_total": len(approvals),
            "approvals_pending": sum(1 for a in approvals if a.state == "pending"),
            "approvals_approved": sum(1 for a in approvals if a.state == "approved"),
            "approvals_rejected": sum(1 for a in approvals if a.state == "rejected"),
            "queue": [a.as_dict() for a in approvals if a.state == "pending"][:20],
        }
