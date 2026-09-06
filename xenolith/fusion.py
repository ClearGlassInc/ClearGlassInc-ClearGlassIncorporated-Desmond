# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH intelligence fusion — observations in, intelligence packets out.

The layer's whole reason to exist is the difference between *data* and
*intelligence*. Raw observations arrive from connectors; what leaves is a
:class:`IntelligencePacket` — clustered, entity-extracted, corroborated,
timelined, with hypotheses ranked by how much independent support they have.

Pipeline:

1. **Ingest.** Connectors yield :class:`Observation` objects. Source
   reliability is a property of the connector, not the observation, so a
   low-grade feed cannot inflate its own credibility.
2. **Extract.** Indicators (IPv4, domain, URL, email, CVE, file hash) are
   pulled from unstructured text and promoted to graph entities.
3. **Cluster.** Observations are grouped by shared indicators first and
   lexical overlap second — two reports about the same IP belong together even
   if they share no vocabulary.
4. **Corroborate.** A cluster seen by several *independent* sources scores
   higher than one source repeating itself.
5. **Hypothesize.** Each cluster yields a plain-language hypothesis with a
   confidence derived from corroboration, source reliability and recency.

Stdlib only.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .constants import LatticeError
from .graph import KnowledgeGraph


class FusionError(LatticeError):
    """A connector or fusion stage failed."""


#: Indicator extractors, most specific first — a CVE must not be shredded into
#: a version number, and a URL must not be reduced to its bare domain.
_EXTRACTORS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cve", re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)),
    ("url", re.compile(r"\bhttps?://[^\s<>\"']{4,}", re.IGNORECASE)),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("sha256", re.compile(r"\b[a-fA-F0-9]{64}\b")),
    ("md5", re.compile(r"\b[a-fA-F0-9]{32}\b")),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
    ("domain", re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b", re.IGNORECASE)),
)

#: Words carrying no discriminating signal for lexical clustering.
_STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those of in on at to from by for with
    is are was were be been being it its as we our they their he she his her you your not
    has have had do does did will would can could should may might must about into over
    """.split()
)

#: Minimum shared-token ratio for two observations to cluster lexically.
LEXICAL_THRESHOLD = 0.34


@dataclass(frozen=True)
class Observation:
    """One raw report from one source, at one moment."""

    source: str
    content: str
    ts: float = field(default_factory=time.time)
    kind: str = "text"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    observation_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source": self.source,
            "kind": self.kind,
            "ts": self.ts,
            "content": self.content,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Indicator:
    """A typed atom extracted from unstructured content."""

    kind: str
    value: str

    def entity_id(self) -> str:
        return f"{self.kind}:{self.value.lower()}"


@dataclass(frozen=True)
class Connector:
    """A plug-in intelligence source.

    ``reliability`` is the analyst's grade for the feed (0.0–1.0) and is applied
    to everything it produces. ``fetch`` returns observations; a connector that
    raises is isolated, not fatal — one broken feed must not stall fusion.
    """

    name: str
    fetch: Callable[[], Iterable[Observation]]
    reliability: float = 0.6
    domain: str = "intelligence"

    def __post_init__(self) -> None:
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be between 0.0 and 1.0")


@dataclass
class Cluster:
    """A set of observations judged to be about the same thing."""

    cluster_id: str
    observations: list[Observation] = field(default_factory=list)
    indicators: set[Indicator] = field(default_factory=set)

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(sorted({o.source for o in self.observations}))

    @property
    def span(self) -> tuple[float, float]:
        stamps = [o.ts for o in self.observations]
        return (min(stamps), max(stamps)) if stamps else (0.0, 0.0)

    def timeline(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {"ts": o.ts, "source": o.source, "summary": _summarize(o.content)}
            for o in sorted(self.observations, key=lambda o: o.ts)
        )


@dataclass(frozen=True)
class Hypothesis:
    """A ranked explanation for a cluster, with the evidence behind it."""

    statement: str
    confidence: float
    corroboration: int
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "confidence": round(self.confidence, 3),
            "corroboration": self.corroboration,
            "indicators": list(self.indicators),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class IntelligencePacket:
    """The unit of output. Actionable, sourced, and dated — not a data dump."""

    packet_id: str
    headline: str
    confidence: float
    hypotheses: tuple[Hypothesis, ...]
    indicators: tuple[str, ...]
    sources: tuple[str, ...]
    timeline: tuple[dict[str, Any], ...]
    generated_at: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "headline": self.headline,
            "confidence": round(self.confidence, 3),
            "hypotheses": [h.as_dict() for h in self.hypotheses],
            "indicators": list(self.indicators),
            "sources": list(self.sources),
            "timeline": list(self.timeline),
            "generated_at": self.generated_at,
        }


class FusionEngine:
    """Ingests observations and produces intelligence packets."""

    def __init__(self, graph: KnowledgeGraph | None = None) -> None:
        self.graph = graph or KnowledgeGraph()
        self._connectors: dict[str, Connector] = {}
        self._observations: list[Observation] = []
        self._reliability: dict[str, float] = {}
        self._failures: list[dict[str, str]] = []
        self._counter = 0

    # ------------------------------------------------------------------ #
    # Connectors
    # ------------------------------------------------------------------ #
    def register_connector(self, connector: Connector) -> Connector:
        if connector.name in self._connectors:
            raise FusionError(f"connector already registered: {connector.name}")
        self._connectors[connector.name] = connector
        self._reliability[connector.name] = connector.reliability
        return connector

    @property
    def connectors(self) -> tuple[Connector, ...]:
        return tuple(self._connectors[name] for name in sorted(self._connectors))

    def collect(self) -> tuple[Observation, ...]:
        """Pull from every connector. A failing connector is isolated, not fatal."""
        collected: list[Observation] = []
        for name in sorted(self._connectors):
            connector = self._connectors[name]
            try:
                for observation in connector.fetch():
                    collected.append(self.ingest(observation, reliability=connector.reliability))
            except Exception as exc:  # noqa: BLE001 - one bad feed must not stop fusion
                self._failures.append({"connector": name, "error": f"{type(exc).__name__}: {exc}"})
        return tuple(collected)

    @property
    def failures(self) -> tuple[dict[str, str], ...]:
        return tuple(self._failures)

    # ------------------------------------------------------------------ #
    # Ingest & extract
    # ------------------------------------------------------------------ #
    def ingest(self, observation: Observation, reliability: float | None = None) -> Observation:
        """Record an observation and promote its indicators into the graph."""
        if not observation.source.strip():
            raise FusionError("observation source is required")
        self._counter += 1
        stored = Observation(
            source=observation.source,
            content=observation.content,
            ts=observation.ts,
            kind=observation.kind,
            metadata=dict(observation.metadata),
            observation_id=observation.observation_id or f"obs-{self._counter:06d}",
        )
        self._observations.append(stored)
        if reliability is not None:
            self._reliability.setdefault(stored.source, reliability)

        grade = self._reliability.get(stored.source, 0.5)
        indicators = extract_indicators(stored.content)
        for indicator in indicators:
            self.graph.upsert_entity(indicator.entity_id(), kind=indicator.kind, labels={stored.source})
            self.graph.assert_fact(
                subject=indicator.entity_id(),
                predicate="observed_by",
                value=stored.source,
                source=stored.source,
                # Several sources observing the same indicator corroborate each
                # other; this predicate must never read as a contradiction.
                multivalued=True,
                confidence=grade,
            )

        # Indicators named in the same report are related by that co-occurrence.
        # This is what turns a bag of extracted atoms into a traversable graph:
        # an analyst pivoting from an IP reaches the CVE it was exploiting.
        for index, left in enumerate(indicators):
            for right in indicators[index + 1 :]:
                if left.entity_id() == right.entity_id():
                    continue
                self.graph.relate(
                    src=left.entity_id(),
                    kind="co_observed",
                    dst=right.entity_id(),
                    source=stored.source,
                    confidence=grade,
                )
        return stored

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._observations)

    # ------------------------------------------------------------------ #
    # Cluster & correlate
    # ------------------------------------------------------------------ #
    def cluster(self) -> tuple[Cluster, ...]:
        """Group observations by shared indicators, then by lexical overlap."""
        clusters: list[Cluster] = []
        index: dict[Indicator, Cluster] = {}

        for observation in sorted(self._observations, key=lambda o: o.ts):
            indicators = set(extract_indicators(observation.content))
            target = next((index[i] for i in indicators if i in index), None)

            if target is None:
                tokens = _tokens(observation.content)
                target = next(
                    (
                        c
                        for c in clusters
                        if not c.indicators
                        and any(_overlap(tokens, _tokens(o.content)) >= LEXICAL_THRESHOLD for o in c.observations)
                    ),
                    None,
                )

            if target is None:
                target = Cluster(cluster_id=f"clu-{len(clusters) + 1:04d}")
                clusters.append(target)

            target.observations.append(observation)
            target.indicators |= indicators
            for indicator in indicators:
                index[indicator] = target

        return tuple(clusters)

    # ------------------------------------------------------------------ #
    # Hypotheses & packets
    # ------------------------------------------------------------------ #
    def hypothesize(self, cluster: Cluster) -> Hypothesis:
        """Turn a cluster into a ranked, reasoned claim."""
        sources = cluster.sources
        corroboration = len(sources)
        reasons: list[str] = [f"{len(cluster.observations)} observations from {corroboration} source(s)"]

        # Independent corroboration dominates: two sources are worth far more
        # than one source reporting twice.
        confidence = 1.0 - (0.55 ** max(1, corroboration))
        grades = [self._reliability.get(s, 0.5) for s in sources]
        mean_grade = sum(grades) / len(grades) if grades else 0.5
        confidence *= 0.4 + 0.6 * mean_grade
        reasons.append(f"mean source reliability {mean_grade:.2f}")

        if cluster.indicators:
            confidence = min(1.0, confidence + 0.08)
            reasons.append(f"{len(cluster.indicators)} hard indicator(s) extracted")

        age_hours = max(0.0, (time.time() - cluster.span[1]) / 3600.0)
        if age_hours > 168:
            confidence *= 0.75
            reasons.append("newest observation is over a week old (-25%)")
        elif age_hours > 24:
            confidence *= 0.9
            reasons.append("newest observation is over a day old (-10%)")

        indicators = tuple(sorted(i.entity_id() for i in cluster.indicators))
        subject = indicators[0] if indicators else _summarize(cluster.observations[0].content)
        statement = (
            f"{subject} is the subject of {len(cluster.observations)} correlated "
            f"observation(s) across {corroboration} source(s)"
        )
        return Hypothesis(
            statement=statement,
            confidence=round(min(1.0, confidence), 4),
            corroboration=corroboration,
            indicators=indicators,
            reasons=tuple(reasons),
        )

    def packets(self, minimum_confidence: float = 0.0) -> tuple[IntelligencePacket, ...]:
        """Produce one packet per cluster, ranked by confidence."""
        built: list[IntelligencePacket] = []
        for cluster in self.cluster():
            if not cluster.observations:
                continue
            hypothesis = self.hypothesize(cluster)
            if hypothesis.confidence < minimum_confidence:
                continue
            built.append(
                IntelligencePacket(
                    packet_id=cluster.cluster_id.replace("clu-", "pkt-"),
                    headline=_summarize(cluster.observations[-1].content, limit=110),
                    confidence=hypothesis.confidence,
                    hypotheses=(hypothesis,),
                    indicators=hypothesis.indicators,
                    sources=cluster.sources,
                    timeline=cluster.timeline(),
                )
            )
        return tuple(sorted(built, key=lambda p: (-p.confidence, p.packet_id)))

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #
    def snapshot(self) -> dict[str, Any]:
        clusters = self.cluster()
        packets = self.packets()
        return {
            "connectors": len(self._connectors),
            "connector_failures": len(self._failures),
            "observations": len(self._observations),
            "clusters": len(clusters),
            "packets": len(packets),
            "top_confidence": round(packets[0].confidence, 3) if packets else 0.0,
            "sources": sorted({o.source for o in self._observations}),
        }


# --------------------------------------------------------------------------- #
# Extraction helpers
# --------------------------------------------------------------------------- #
def extract_indicators(text: str) -> tuple[Indicator, ...]:
    """Pull typed indicators from free text, most specific pattern first.

    Spans already claimed by a more specific extractor are masked out, so
    ``https://evil.example/x`` yields a URL and not also a bare domain.
    """
    if not text:
        return ()
    remaining = text
    found: list[Indicator] = []
    seen: set[tuple[str, str]] = set()
    for kind, pattern in _EXTRACTORS:
        for match in pattern.finditer(remaining):
            value = match.group(0)
            key = (kind, value.lower())
            if key in seen:
                continue
            seen.add(key)
            found.append(Indicator(kind=kind, value=value))
        remaining = pattern.sub(lambda m: " " * len(m.group(0)), remaining)
    return tuple(found)


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _overlap(left: set[str], right: set[str]) -> float:
    """Jaccard similarity; 0.0 when either side has no usable tokens."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _summarize(text: str, limit: int = 90) -> str:
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1].rstrip() + "…"
