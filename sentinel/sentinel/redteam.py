"""SENTINEL — adversarial input scorer (SABER S_threat).

A lightweight, deterministic secondary check that scores a query for
prompt-injection / exfiltration / spoofing intent in [0, 1]. In production
this is a dedicated red-team model; the heuristic here keeps the scaffold
runnable and the tests deterministic. Raising is treated as fail-closed by
the Governance Shell (unverifiable threat -> deny).
"""
from __future__ import annotations

import re
from typing import Protocol

_PATTERNS = [
    r"ignore (the )?(previous|prior|above) (instructions|prompt)",
    r"disregard .*(rules|policy|instructions)",
    r"reveal .*(system prompt|hidden|instructions)",
    r"show .*(credential|password|secret|api[ _-]?key|token)",
    r"exfiltrat",
    r"bypass .*(policy|guardrail|approval|auth)",
    r"\bact as\b .*(admin|root|system)",
    r"pretend you are",
    r"override .*(permission|boundary|clearance)",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


class ThreatScorer(Protocol):
    def score(self, text: str) -> float: ...


class HeuristicRedTeam:
    def score(self, text: str) -> float:
        hits = sum(1 for rx in _COMPILED if rx.search(text))
        if hits == 0:
            return 0.05
        # saturating: each matched adversarial pattern raises the score steeply.
        return min(1.0, 0.5 + 0.25 * hits)
