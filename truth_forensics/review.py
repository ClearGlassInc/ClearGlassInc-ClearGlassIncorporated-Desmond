# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass Forensic Review: human-in-the-loop decisions, append-only.

A review never edits a finding. It appends a record, hash-chained like the
provenance ledger, and every final status is derived by replaying the log:

    AI / analyzer output + human review = final status

Rules enforced here:

* Separation of duties: the analyst who ran the analysis cannot ACCEPT,
  REJECT or MARK_INCONCLUSIVE it.
* A REQUEST_SECOND_REVIEW blocks finalisation until a different reviewer
  (not the requester, not the analyst) makes a decision.
* Nothing becomes VERIFIED without a human ACCEPT. Demonstration data is
  SIMULATED whatever a reviewer does.

Targets: an evidence id (`EV-A`), a finding id (`EV-A#TEMPORAL.EDIT_LIST`),
or `CLAIM`.
"""
from __future__ import annotations

from . import vocab
from .canonical import GENESIS_HASH, canonical_json, sha256_text

ACTIONS = ("ACCEPT", "REJECT", "ESCALATE", "MARK_INCONCLUSIVE", "ADD_EVIDENCE", "ANNOTATE",
           "COMMENT", "REQUEST_SECOND_REVIEW")
DECISIVE = ("ACCEPT", "REJECT", "MARK_INCONCLUSIVE")


class ReviewError(ValueError):
    pass


class ReviewLog:
    def __init__(self, analyst: str, records: list[dict] | None = None) -> None:
        self.analyst = analyst
        self._records: list[dict] = []
        for rec in records or []:
            self.record(rec["action"], rec["target"], rec["reviewer"], rec["at"],
                        rec.get("note", ""))

    @property
    def records(self) -> list[dict]:
        return [dict(r) for r in self._records]

    @property
    def head(self) -> str:
        return self._records[-1]["record_hash"] if self._records else GENESIS_HASH

    def record(self, action: str, target: str, reviewer: str, at: str, note: str = "") -> dict:
        if action not in ACTIONS:
            raise ReviewError(f"unknown review action '{action}'")
        reviewer = (reviewer or "").strip()
        target = (target or "").strip()
        if not reviewer or not target:
            raise ReviewError("a review needs a reviewer and a target")
        if len(note) > 2000:
            raise ReviewError("review note exceeds 2000 characters")
        if action in DECISIVE:
            if reviewer == self.analyst:
                raise ReviewError("separation of duties: the analyst cannot decide their own "
                                  "analysis")
            pending = self._open_second_review(target)
            if pending and reviewer == pending:
                raise ReviewError("a second review must come from a different reviewer")
        body = {"seq": len(self._records) + 1, "action": action, "target": target,
                "reviewer": reviewer, "at": at, "note": note}
        rec = {**body, "prev_hash": self.head,
               "record_hash": sha256_text(self.head + canonical_json(body))}
        self._records.append(rec)
        return dict(rec)

    def _open_second_review(self, target: str) -> str:
        requester = ""
        for r in self._records:
            if r["target"] != target:
                continue
            if r["action"] == "REQUEST_SECOND_REVIEW":
                requester = r["reviewer"]
            elif r["action"] in DECISIVE and requester and r["reviewer"] != requester:
                requester = ""
        return requester

    def history(self, target: str) -> list[dict]:
        return [dict(r) for r in self._records if r["target"] == target]

    def decision(self, target: str) -> dict:
        """Latest decisive action and the review state of a target."""
        last = None
        state = "PENDING"
        for r in self._records:
            if r["target"] != target:
                continue
            if r["action"] in DECISIVE:
                last = r
                state = "DECIDED"
            elif r["action"] == "ESCALATE":
                state = "ESCALATED"
        if self._open_second_review(target):
            state = "AWAITING_SECOND_REVIEW"
        return {"state": state, "action": last["action"] if last and state == "DECIDED" else "",
                "reviewer": last["reviewer"] if last and state == "DECIDED" else "",
                "at": last["at"] if last and state == "DECIDED" else "",
                "note": last["note"] if last and state == "DECIDED" else ""}

    def verify(self) -> tuple[bool, int | None]:
        prev = GENESIS_HASH
        for i, r in enumerate(self._records, start=1):
            body = {k: r[k] for k in ("seq", "action", "target", "reviewer", "at", "note")}
            if r["prev_hash"] != prev or r["record_hash"] != sha256_text(prev + canonical_json(body)):
                return False, i
            prev = r["record_hash"]
        return True, None


def final_status(proposed: str, decision: dict, demonstration: bool) -> str:
    """Analysis-proposed status + human decision -> final evidence status."""
    if demonstration:
        return vocab.SIMULATED
    if decision["state"] == "PENDING":
        # Analysis alone never verifies anything.
        return vocab.SUPPORTED if proposed == vocab.VERIFIED else proposed
    if decision["state"] != "DECIDED":
        return vocab.INCONCLUSIVE
    if decision["action"] == "REJECT":
        return vocab.UNVERIFIED
    if decision["action"] == "MARK_INCONCLUSIVE":
        return vocab.INCONCLUSIVE
    return proposed
