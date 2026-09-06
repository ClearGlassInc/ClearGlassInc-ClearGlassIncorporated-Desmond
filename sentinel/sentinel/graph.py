"""PERCIVAL Agent Mesh — entity/topic graph (organizations & assets only).

A small, dependency-free graph for the Entity-Link agent: nodes are
organizations / brands / domains / facilities / infrastructure / topics /
sources, edges are typed relationships with a confidence weight.

PRIVACY GUARDRAIL: person/individual node types are REJECTED. This graph is for
corporate/asset entity linking, never for building dossiers on people.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional

ALLOWED_TYPES = frozenset({
    "organization", "brand", "domain", "facility", "infrastructure",
    "asset", "topic", "source", "vulnerability", "incident",
})
PERSON_TYPES = frozenset({"person", "individual", "human", "people"})


class GraphError(Exception):
    pass


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    label: str = ""


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str
    confidence: float = 0.5


class EntityGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._adj: dict[str, list[Edge]] = {}

    # --- build ---------------------------------------------------------------
    def add_node(self, node: Node) -> Node:
        t = (node.type or "").strip().lower()
        if t in PERSON_TYPES:
            raise GraphError("person/individual nodes are not permitted (charter)")
        if t not in ALLOWED_TYPES:
            raise GraphError(f"node type '{node.type}' is not allowed")
        canon = Node(node.id, t, node.label or node.id)
        self._nodes[node.id] = canon
        self._adj.setdefault(node.id, [])
        return canon

    def add_edge(self, src: str, dst: str, kind: str, confidence: float = 0.5) -> Edge:
        if src not in self._nodes or dst not in self._nodes:
            raise GraphError("both endpoints must be added as nodes first")
        e = Edge(src, dst, kind, round(max(0.0, min(1.0, confidence)), 3))
        self._adj[src].append(e)
        self._adj[dst].append(Edge(dst, src, kind, e.confidence))   # undirected store
        return e

    # --- query ---------------------------------------------------------------
    def neighbors(self, node_id: str) -> list[Edge]:
        return list(self._adj.get(node_id, []))

    def degree(self, node_id: str) -> int:
        return len(self._adj.get(node_id, []))

    def path(self, a: str, b: str) -> Optional[list[str]]:
        """Shortest path (BFS) between two nodes, or None."""
        if a not in self._nodes or b not in self._nodes:
            return None
        if a == b:
            return [a]
        seen = {a}
        q: deque[list[str]] = deque([[a]])
        while q:
            p = q.popleft()
            for e in self._adj[p[-1]]:
                if e.dst == b:
                    return p + [b]
                if e.dst not in seen:
                    seen.add(e.dst)
                    q.append(p + [e.dst])
        return None

    def top_connected(self, k: int = 5) -> list[tuple[str, int]]:
        ranked = sorted(((nid, self.degree(nid)) for nid in self._nodes),
                        key=lambda t: (-t[1], t[0]))
        return ranked[:k]

    def to_dict(self) -> dict:
        seen: set[tuple[str, str, str]] = set()
        edges = []
        for src, es in self._adj.items():
            for e in es:
                key = (min(e.src, e.dst), max(e.src, e.dst), e.kind)
                if key in seen:
                    continue
                seen.add(key)
                edges.append({"src": e.src, "dst": e.dst, "kind": e.kind, "confidence": e.confidence})
        return {
            "nodes": [{"id": n.id, "type": n.type, "label": n.label} for n in self._nodes.values()],
            "edges": edges,
        }


def graph_from_signals(entity: str, signals, *, topics: Optional[list[str]] = None) -> EntityGraph:
    """Build a corporate-entity graph from collector Signals: the target entity
    links to each source, and to any supplied topics."""
    g = EntityGraph()
    g.add_node(Node(entity, "organization", entity))
    sources = {s.source for s in signals}
    for src in sources:
        sid = "src:" + src
        g.add_node(Node(sid, "source", src))
        # confidence = max signal confidence from that source
        conf = max((s.confidence for s in signals if s.source == src), default=0.5)
        g.add_edge(entity, sid, "mentioned_in", conf)
    for t in (topics or []):
        tid = "topic:" + t
        g.add_node(Node(tid, "topic", t))
        g.add_edge(entity, tid, "associated_with", 0.6)
    return g
