# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Explainable indicators.

An indicator answers six questions, and the constructor refuses one that
leaves any of them blank:

    WHAT WAS FOUND?                       title
    HOW WAS IT FOUND?                     method
    WHAT EVIDENCE SUPPORTS IT?            evidence
    HOW CONFIDENT IS THE SYSTEM?          confidence (LOW / MODERATE / HIGH)
    WHAT COULD EXPLAIN THE SAME SIGNAL?   alternatives
    WHAT CAN THE SYSTEM NOT DETERMINE?    limitation

An indicator is an observation about the bytes. It is never a verdict about
the event the bytes are said to depict.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import vocab

# Editor and generator names matched case-insensitively in software tags.
# Presence means the file says it passed through that software. Absence
# means nothing: tags are trivially stripped or rewritten.
EDITOR_NAMES = (
    "photoshop", "lightroom", "gimp", "affinity", "pixelmator", "snapseed", "facetune",
    "canva", "picsart", "paint.net", "darktable", "capture one", "luminar", "photopea",
    "premiere", "after effects", "davinci", "final cut", "imovie", "capcut", "handbrake",
    "lavf", "ffmpeg", "audacity", "adobe audition",
)
GENERATOR_NAMES = (
    "dall-e", "dall·e", "midjourney", "stable diffusion", "firefly", "imagen",
    "novelai", "comfyui", "automatic1111", "sora", "runway", "elevenlabs",
)


@dataclass(frozen=True)
class Indicator:
    code: str
    category: str
    title: str
    evidence: str
    method: str
    confidence: str
    limitation: str
    alternatives: tuple[str, ...]
    state: str
    analyzer: str
    location: str = ""
    finding_id: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        for name in ("code", "title", "evidence", "method", "limitation", "analyzer"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"indicator {self.code or '?'} has no {name}")
        if not self.alternatives:
            raise ValueError(f"indicator {self.code} lists no alternative explanation")
        if self.category not in vocab.CATEGORIES:
            raise ValueError(f"unknown category {self.category}")
        if self.confidence not in ("LOW", "MODERATE", "HIGH"):
            raise ValueError(f"indicator confidence must be LOW, MODERATE or HIGH: {self.confidence}")
        if self.state not in vocab.STATES:
            raise ValueError(f"unknown state {self.state}")

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "code": self.code,
            "category": self.category,
            "title": self.title,
            "evidence": self.evidence,
            "method": self.method,
            "confidence": self.confidence,
            "limitation": self.limitation,
            "alternatives": list(self.alternatives),
            "state": self.state,
            "analyzer": self.analyzer,
            "location": self.location,
        }


def quote(value: str) -> str:
    """Single-quoted, backslash-escaped. Same bytes in the browser engine."""
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def parse_message(exc: Exception) -> str:
    """Parser failures surface as their own message, or a fixed phrase for
    low-level unpacking errors, so no interpreter text reaches a report."""
    return str(exc) if type(exc).__name__ == "ParseError" else "structure truncated"


def match_names(text: str, names: tuple[str, ...]) -> list[str]:
    low = text.lower()
    return [name for name in names if name in low]


def software_indicators(field_name: str, value: str, analyzer: str) -> list[Indicator]:
    """Editor / generator names in a software-style metadata field."""
    out: list[Indicator] = []
    generators = match_names(value, GENERATOR_NAMES)
    if generators:
        out.append(Indicator(
            code="SYNTHETIC.GENERATOR_TAG",
            category="SYNTHETIC",
            title="Metadata names a generative-media tool",
            evidence=f"{field_name} = {quote(value)} (matched: {', '.join(generators)})",
            method="Case-insensitive match of software metadata against a list of generator names.",
            confidence="MODERATE",
            limitation=(
                "Metadata can be written, copied or removed by anyone. A tag is not proof of "
                "generation, and its absence is not evidence of capture."
            ),
            alternatives=(
                "A captured file re-saved through the named tool",
                "Metadata copied from another file",
            ),
            state=vocab.REVIEW_REQUIRED,
            analyzer=analyzer,
        ))
    editors = match_names(value, EDITOR_NAMES)
    if editors:
        out.append(Indicator(
            code="METADATA.EDITING_SOFTWARE",
            category="METADATA",
            title="File was last written by editing or transcoding software",
            evidence=f"{field_name} = {quote(value)} (matched: {', '.join(editors)})",
            method="Case-insensitive match of software metadata against a list of editor names.",
            confidence="MODERATE",
            limitation=(
                "Shows which program wrote the file, not what it changed. Routine export, "
                "resizing and platform transcoding produce the same tag."
            ),
            alternatives=(
                "Routine export or colour correction",
                "Platform or messaging-app transcoding",
                "Format conversion for storage",
            ),
            state=vocab.REVIEW_REQUIRED,
            analyzer=analyzer,
        ))
    return out


def trailing_data_indicator(extra: int, marker: str, analyzer: str) -> Indicator:
    return Indicator(
        code="CONTAINER.TRAILING_DATA",
        category="CONTAINER",
        title=f"Data present after the {marker} end marker",
        evidence=f"{extra} byte(s) follow the {marker} marker",
        method="Structural parse of the container to its end-of-image marker.",
        confidence="HIGH",
        limitation=(
            "The trailing bytes are counted, not analysed. Their content and origin are unknown."
        ),
        alternatives=(
            "Vendor trailer (for example a motion-photo video or depth map)",
            "Appended data from a later tool",
            "Incomplete overwrite of a longer file",
        ),
        state=vocab.REVIEW_REQUIRED,
        analyzer=analyzer,
    )


def parse_error_indicator(detail: str, analyzer: str) -> Indicator:
    return Indicator(
        code="CONTAINER.PARSE_ERROR",
        category="CONTAINER",
        title="Container could not be fully parsed",
        evidence=detail,
        method="Bounds-checked structural parse; parsing stopped at the first inconsistency.",
        confidence="HIGH",
        limitation="Analysis after the failure point did not run. Results are incomplete.",
        alternatives=(
            "Truncated transfer or storage corruption",
            "A format variant this analyzer does not support",
            "Deliberately malformed input",
        ),
        state=vocab.INCONCLUSIVE,
        analyzer=analyzer,
    )


def assign_finding_ids(evidence_id: str, indicators: list[Indicator]) -> list[Indicator]:
    """Stable ids: `<evidence_id>#<code>`, with `~n` for repeats."""
    seen: dict[str, int] = {}
    out = []
    for ind in indicators:
        seen[ind.code] = seen.get(ind.code, 0) + 1
        suffix = "" if seen[ind.code] == 1 else f"~{seen[ind.code]}"
        out.append(_with_id(ind, f"{evidence_id}#{ind.code}{suffix}"))
    return out


def _with_id(ind: Indicator, finding_id: str) -> Indicator:
    data = ind.to_dict()
    data.pop("finding_id")
    data["alternatives"] = tuple(data["alternatives"])
    return Indicator(finding_id=finding_id, **data)
