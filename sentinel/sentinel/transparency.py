"""AEGIS — transparency-report generator.

Summarizes a legal-process register (request + AEGIS assessment) into a
publishable transparency report: counts by request type and outcome, how many
demands were challenged vs complied-with (pending counsel), refusals, and how
many named a protected principal. Markdown for publication; JSON for archival.

Aggregate-only by design — it reports COUNTS, never the content of any request
or any disclosed data.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass

from .legalshield import DISCLAIMER, Outcome, RegisterEntry, RequestKind


@dataclass
class TransparencyReport:
    period: str
    generated_utc: str
    total_requests: int
    by_kind: dict[str, int]
    by_outcome: dict[str, int]
    challenged: int
    complied_pending_counsel: int
    refused: int
    preserved: int
    protected_principal_named: int
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return {
            "period": self.period, "generated_utc": self.generated_utc,
            "total_requests": self.total_requests, "by_kind": self.by_kind,
            "by_outcome": self.by_outcome, "challenged": self.challenged,
            "complied_pending_counsel": self.complied_pending_counsel,
            "refused": self.refused, "preserved": self.preserved,
            "protected_principal_named": self.protected_principal_named,
            "disclaimer": self.disclaimer,
        }


def build_report(register: list[RegisterEntry], *, period: str) -> TransparencyReport:
    by_kind: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    challenged = complied = refused = preserved = protected = 0

    for e in register:
        k = e.request.kind.value
        o = e.assessment.outcome
        by_kind[k] = by_kind.get(k, 0) + 1
        by_outcome[o.value] = by_outcome.get(o.value, 0) + 1
        if o is Outcome.CHALLENGE:
            challenged += 1
        elif o is Outcome.COMPLY_PENDING_COUNSEL:
            complied += 1
        elif o in (Outcome.REFUSE_NO_LEGAL_BASIS, Outcome.REFUSE_UNLAWFUL):
            refused += 1
        elif o is Outcome.PRESERVE_IN_PLACE:
            preserved += 1
        if e.assessment.protected_principal:
            protected += 1

    return TransparencyReport(
        period=period,
        generated_utc=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        total_requests=len(register),
        by_kind=by_kind, by_outcome=by_outcome,
        challenged=challenged, complied_pending_counsel=complied,
        refused=refused, preserved=preserved,
        protected_principal_named=protected,
    )


def report_json(report: TransparencyReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def report_markdown(report: TransparencyReport, *,
                    org: str = "ClearGlass Inc.") -> str:
    out: list[str] = [
        f"# {org} — Legal-Process Transparency Report",
        "",
        f"- **Period:** {report.period}",
        f"- **Generated (UTC):** {report.generated_utc}",
        f"- **Total requests received:** {report.total_requests}",
        "",
        "## Outcomes",
        "",
        f"- Complied (pending counsel sign-off): **{report.complied_pending_counsel}**",
        f"- Challenged (defective / overbroad / expired): **{report.challenged}**",
        f"- Preserved in place (legal hold): **{report.preserved}**",
        f"- Refused (no legal basis / unlawful): **{report.refused}**",
        f"- Named a protected principal: **{report.protected_principal_named}**",
        "",
        "## By request type",
        "",
    ]
    out += [f"- {RequestKind(k).value if k in RequestKind._value2member_map_ else k}: {v}"
            for k, v in sorted(report.by_kind.items())] or ["- (none)"]
    out += ["", "## By outcome", ""]
    out += [f"- {k}: {v}" for k, v in sorted(report.by_outcome.items())] or ["- (none)"]
    out += [
        "",
        "---",
        f"*{report.disclaimer}*",
        "",
        "*Aggregate counts only — no request content or disclosed data is included.*",
    ]
    return "\n".join(out) + "\n"
