#!/usr/bin/env python3
"""Evidence-backed ClearGlass site intelligence graph.

This is the runtime authority for the Intelligence Graph.  It deliberately
extends the existing static IA instead of replacing it.

Sources
-------
1. GitHub repository tree + HTML blobs at an immutable commit (github_api).
2. Live sitemap.xml (sitemap).
3. Optional rendered DOM crawl with Playwright (rendered_dom).

The first two sources are sufficient for node corroboration.  Edges are
corroborated when the same relationship is observed in GitHub HTML and the
rendered DOM crawl.  A source that cannot be reached is recorded explicitly;
the tool never silently upgrades confidence.

Analytics are computed by NetworkX:
- PageRank: nx.pagerank
- Betweenness: nx.betweenness_centrality
- Community detection: nx.community.louvain_communities
- Modularity: nx.community.modularity

Storage
-------
data/intelligence-graph/site_graph_v<TIMESTAMP>.json
data/intelligence-graph/site_graph_latest.json
data/intelligence-graph/snapshots/index.json
data/intelligence-graph/audit.jsonl

Commands
--------
python3 tools/site_intelligence_graph.py crawl
python3 tools/site_intelligence_graph.py diff <date_a> <date_b>
python3 tools/site_intelligence_graph.py verify-chain
python3 tools/site_intelligence_graph.py self-test
"""
from __future__ import annotations

import argparse
import base64
import collections
import hashlib
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import networkx as nx
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "intelligence-graph"
SNAPSHOT_DIR = OUT_DIR / "snapshots"
LATEST_PATH = OUT_DIR / "site_graph_latest.json"
INDEX_PATH = SNAPSHOT_DIR / "index.json"
AUDIT_PATH = OUT_DIR / "audit.jsonl"

SITE_ROOT = os.getenv("CG_GRAPH_SITE_ROOT", "https://www.clearglassinc.com").rstrip("/")
SITE_SITEMAP = os.getenv("CG_GRAPH_SITEMAP", f"{SITE_ROOT}/sitemap.xml")
GITHUB_REPO = os.getenv(
    "CG_GRAPH_GITHUB_REPO",
    "ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond",
)
GITHUB_REF = os.getenv("CG_GRAPH_GITHUB_REF", "main")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
USER_AGENT = os.getenv(
    "CG_GRAPH_USER_AGENT",
    "ClearGlass-Intelligence-Graph/1.0 (+https://www.clearglassinc.com/)",
)
REQUEST_TIMEOUT = float(os.getenv("CG_GRAPH_TIMEOUT_SECONDS", "20"))
MAX_BODY_BYTES = int(os.getenv("CG_GRAPH_MAX_BODY_BYTES", str(2_000_000)))
MAX_PAGES = int(os.getenv("CG_GRAPH_MAX_PAGES", "400"))
MAX_LINKS_PER_PAGE = int(os.getenv("CG_GRAPH_MAX_LINKS_PER_PAGE", "800"))
RATE_DELAY = float(os.getenv("CG_GRAPH_MIN_DELAY_SECONDS", "0.20"))
PLAYWRIGHT_ENABLED = os.getenv("CG_GRAPH_RENDERED_DOM", "1").lower() in {"1", "true", "yes"}
LOUVAIN_SEED = int(os.getenv("CG_GRAPH_LOUVAIN_SEED", "42"))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_hash_view(value: Any) -> Any:
    """Canonical, deterministic hash view shared with the browser verifier.

    All JSON numbers are represented as compact decimal strings so a browser
    verifier (which does not preserve Python's int-vs-float distinction) can
    reproduce the exact same SHA-256 inputs.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == 0:
            return "0"
        return format(value, ".12f").rstrip("0").rstrip(".")
    if isinstance(value, dict):
        return {str(k): canonical_hash_view(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonical_hash_view(v) for v in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_hash_view(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def record_hash(record: dict[str, Any], field: str) -> str:
    clean = {k: v for k, v in record.items() if k != field}
    return sha256_text(canonical_json(clean))


def confidence_for_sources(count: int) -> float:
    return {0: 0.0, 1: 0.55, 2: 0.85}.get(count, 1.0)


def safe_intent_label(path: str) -> str:
    if path == "index.html":
        return "company"
    if path.startswith("blog/"):
        return "insights"
    if path.startswith("offers/") or path in {"pricing.html", "store.html", "products.html"}:
        return "services"
    if path.startswith("legal/"):
        return "legal"
    if path.startswith("operations/"):
        return "operations"
    if path.startswith("investors/"):
        return "company"
    return "site"


class CrawlError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceEvidence:
    name: str
    url: str
    retrieved_at: str
    status: str
    detail: str = ""
    payload_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "retrieved_at": self.retrieved_at,
            "status": self.status,
            "detail": self.detail,
            **({"payload_hash": self.payload_hash} if self.payload_hash else {}),
        }


@dataclass(frozen=True)
class ParsedPage:
    url: str
    title: str
    description: str
    word_count: int
    content_hash: str
    links: tuple[tuple[str, str, str], ...]  # target, link_type, anchor


def normalize_url(url: str, base: str = SITE_ROOT) -> str | None:
    if not url:
        return None
    url = unescape(url.strip())
    if url.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None
    absolute = urljoin(base + "/", url)
    absolute, _fragment = urldefrag(absolute)
    parts = urlsplit(absolute)
    if parts.scheme not in {"http", "https"}:
        return None
    if parts.netloc.lower() != urlsplit(SITE_ROOT).netloc.lower():
        return None
    path = parts.path or "/"
    if path == "/":
        path = "/index.html"
    if path.endswith("/"):
        path += "index.html"
    if not re.search(r"\.html?$", path, re.IGNORECASE):
        return None
    path = re.sub(r"/+", "/", path)
    return urlunsplit((urlsplit(SITE_ROOT).scheme, urlsplit(SITE_ROOT).netloc, path, "", ""))


def site_path(url: str) -> str | None:
    normalized = normalize_url(url)
    if not normalized:
        return None
    path = urlsplit(normalized).path.lstrip("/")
    return path or "index.html"


def link_type_for(anchor: Any) -> str:
    for parent in anchor.parents:
        if getattr(parent, "name", None) in {"nav", "header"}:
            return "navigation"
        if getattr(parent, "name", None) == "footer":
            return "footer"
        classes = " ".join(parent.get("class", []) if hasattr(parent, "get") else [])
        marker = f" {classes.casefold()} "
        if " cg-related " in marker or " related " in marker:
            return "related"
        if " cta " in marker or "cta" in marker:
            return "cta"
        if getattr(parent, "name", None) in {"main", "article", "section"}:
            return "content"
    return "document"


def parse_html(url: str, body: bytes) -> ParsedPage:
    if len(body) > MAX_BODY_BYTES:
        raise CrawlError(f"body exceeds {MAX_BODY_BYTES} byte safety cap")
    content_hash = hashlib.sha256(body).hexdigest()
    text = body.decode("utf-8", errors="replace")
    soup = BeautifulSoup(text, "html.parser")
    title = " ".join(soup.title.get_text(" ", strip=True).split()) if soup.title else ""
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = ""
    if meta and meta.get("content"):
        description = " ".join(str(meta["content"]).split())
    visible_root = soup.body or soup
    for tag in visible_root(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    words = re.findall(r"\b[\w’'-]+\b", visible_root.get_text(" ", strip=True), flags=re.UNICODE)
    links: list[tuple[str, str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", ""))
        target = normalize_url(href, url)
        if not target or target == url:
            continue
        target_path = site_path(target)
        if not target_path:
            continue
        label = " ".join(anchor.get_text(" ", strip=True).split())
        links.append((target, link_type_for(anchor), label[:300]))
        if len(links) >= MAX_LINKS_PER_PAGE:
            break
    return ParsedPage(
        url=url,
        title=title[:500],
        description=description[:1000],
        word_count=len(words),
        content_hash=content_hash,
        links=tuple(links),
    )


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.7",
            "Accept-Language": "en-CA,en;q=0.8",
            "X-ClearGlass-Graph-Collector": "site-intelligence-v1",
        }
    )
    if GITHUB_TOKEN:
        session.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return session


def request_bytes(session: requests.Session, url: str, accept: str | None = None) -> tuple[bytes, str, dict[str, str]]:
    headers = {}
    if accept:
        headers["Accept"] = accept
    response = session.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
    response.raise_for_status()
    raw = response.content
    if len(raw) > MAX_BODY_BYTES:
        raise CrawlError(f"response exceeds {MAX_BODY_BYTES} byte safety cap: {url}")
    return raw, response.headers.get("content-type", ""), dict(response.headers)


def github_api_json(session: requests.Session, path: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path.lstrip('/')}"
    raw, _ct, _headers = request_bytes(
        session,
        url,
        "application/vnd.github+json",
    )
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise CrawlError(f"invalid GitHub JSON from {url}: {exc}") from exc


def github_snapshot(session: requests.Session, retrieved_at: str) -> tuple[str, dict[str, Any], dict[str, ParsedPage], SourceEvidence]:
    ref = github_api_json(session, f"git/ref/heads/{GITHUB_REF}")
    commit_sha = ref.get("object", {}).get("sha")
    if not commit_sha:
        raise CrawlError(f"GitHub ref did not resolve to a commit: {GITHUB_REF}")
    tree = github_api_json(session, f"git/trees/{commit_sha}?recursive=1")
    if tree.get("truncated"):
        raise CrawlError("GitHub tree is truncated; refusing to infer the full site graph")
    html_entries = [
        item for item in tree.get("tree", [])
        if item.get("type") == "blob"
        and str(item.get("path", "")).lower().endswith(".html")
    ]
    html_entries = sorted(html_entries, key=lambda item: item["path"])[:MAX_PAGES]
    pages: dict[str, ParsedPage] = {}
    failures: list[str] = []

    def fetch_entry(item: dict[str, Any]) -> tuple[str, ParsedPage | None, str | None]:
        local = make_session()
        path = item["path"]
        blob_sha = item["sha"]
        try:
            obj = github_api_json(local, f"git/blobs/{blob_sha}")
            if obj.get("encoding") != "base64":
                raise CrawlError(f"unexpected GitHub blob encoding: {obj.get('encoding')}")
            body = base64.b64decode(obj.get("content", ""), validate=False)
            page_url = normalize_url(f"{SITE_ROOT}/{path}")
            if not page_url:
                return path, None, "non-indexable path"
            return path, parse_html(page_url, body), None
        except Exception as exc:  # recorded as source failure, never hidden
            return path, None, str(exc)

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(html_entries)))) as pool:
        futures = [pool.submit(fetch_entry, item) for item in html_entries]
        for future in as_completed(futures):
            path, parsed, error = future.result()
            if parsed:
                pages[path] = parsed
            else:
                failures.append(f"{path}: {error}")

    evidence = SourceEvidence(
        name="github_api",
        url=f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{commit_sha}?recursive=1",
        retrieved_at=retrieved_at,
        status="ok" if not failures else "partial",
        detail=f"commit={commit_sha}; html_files={len(html_entries)}; parsed={len(pages)}; failures={len(failures)}"
        + (f"; {failures[:5]}" if failures else ""),
        payload_hash=sha256_text(canonical_json(tree)),
    )
    return commit_sha, tree, pages, evidence


def sitemap_pages(session: requests.Session, retrieved_at: str) -> tuple[set[str], dict[str, str], list[SourceEvidence]]:
    queue = [SITE_SITEMAP]
    seen: set[str] = set()
    pages: set[str] = set()
    lastmods: dict[str, str] = {}
    evidences: list[SourceEvidence] = []
    failures: list[str] = []

    while queue and len(seen) < 50:
        sitemap = queue.pop(0)
        if sitemap in seen:
            continue
        seen.add(sitemap)
        try:
            raw, _ct, _headers = request_bytes(session, sitemap, "application/xml,text/xml;q=0.9,*/*;q=0.2")
            root = ET.fromstring(raw)
            locs = root.findall(".//{*}loc")
            child_sitemaps = root.findall(".//{*}sitemap")
            has_urlset = bool(root.findall(".//{*}url"))
            if child_sitemaps and not has_urlset:
                for entry in child_sitemaps:
                    loc = (entry.findtext("{*}loc") or "").strip()
                    if loc:
                        queue.append(loc)
            for entry in root.findall(".//{*}url"):
                loc = (entry.findtext("{*}loc") or "").strip()
                path = site_path(loc)
                if path:
                    pages.add(path)
                    last = (entry.findtext("{*}lastmod") or "").strip()
                    if last:
                        lastmods[path] = last
            evidences.append(
                SourceEvidence(
                    name="sitemap",
                    url=sitemap,
                    retrieved_at=retrieved_at,
                    status="ok",
                    detail=f"index_entries={len(locs)}; page_urls={len(pages)}",
                    payload_hash=sha256_text(raw.decode("utf-8", errors="replace")),
                )
            )
        except Exception as exc:
            failures.append(f"{sitemap}: {exc}")

    if failures:
        evidences.append(
            SourceEvidence(
                name="sitemap",
                url=SITE_SITEMAP,
                retrieved_at=retrieved_at,
                status="failed",
                detail="; ".join(failures[:8]),
            )
        )
    if not pages:
        raise CrawlError("live sitemap produced no indexable HTML URLs")
    return pages, lastmods, evidences


def rendered_dom_pages(
    targets: set[str],
    retrieved_at: str,
) -> tuple[dict[str, ParsedPage], list[SourceEvidence]]:
    if not PLAYWRIGHT_ENABLED:
        return {}, [
            SourceEvidence(
                "rendered_dom",
                SITE_ROOT,
                retrieved_at,
                "disabled",
                "CG_GRAPH_RENDERED_DOM is disabled",
            )
        ]
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {}, [
            SourceEvidence(
                "rendered_dom",
                SITE_ROOT,
                retrieved_at,
                "unavailable",
                f"Playwright import failed: {exc}",
            )
        ]

    pages: dict[str, ParsedPage] = {}
    failures: list[str] = []
    ordered = sorted(targets)[:MAX_PAGES]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="en-CA",
            java_script_enabled=True,
            ignore_https_errors=False,
        )
        page = context.new_page()
        for path in ordered:
            url = normalize_url(f"{SITE_ROOT}/{path}")
            if not url:
                continue
            if RATE_DELAY:
                time.sleep(RATE_DELAY + (int(sha256_text(path)[:4], 16) % 10) / 1000)
            dom_url = url + ("&" if "?" in url else "?") + "skipboot=1"
            try:
                page.goto(dom_url, wait_until="domcontentloaded", timeout=int(REQUEST_TIMEOUT * 1000))
                page.wait_for_timeout(250)
                body = page.content().encode("utf-8")
                pages[path] = parse_html(url, body)
            except Exception as exc:
                failures.append(f"{path}: {exc}")
        context.close()
        browser.close()

    return pages, [
        SourceEvidence(
            "rendered_dom",
            SITE_ROOT,
            retrieved_at,
            "ok" if not failures else "partial",
            f"targets={len(ordered)}; parsed={len(pages)}; failures={len(failures)}"
            + (f"; {failures[:5]}" if failures else ""),
        )
    ]


def declared_ia() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, Any]]]:
    """Read the declared IA without making it authoritative over observed data."""
    pages: dict[str, dict[str, str]] = {}
    clusters: dict[str, dict[str, Any]] = {}
    try:
        from tools import internal_links as legacy  # type: ignore
        for path, (title, description) in legacy.PAGES.items():
            pages[path] = {
                "title": title,
                "description": description,
                "sector": legacy.cluster_of(path),
            }
        clusters = {
            cid: {
                "name": c["name"],
                "pillar": c["pillar"],
                "members": list(c["members"]),
                "cta": list(c["cta"]),
            }
            for cid, c in legacy.CLUSTERS.items()
        }
        return pages, clusters
    except Exception:
        pass

    index_path = ROOT / "data" / "site-index.json"
    if not index_path.is_file():
        return pages, clusters
    obj = json.loads(index_path.read_text(encoding="utf-8"))
    for cluster in obj.get("clusters", []):
        cid = str(cluster.get("id", ""))
        if not cid:
            continue
        clusters[cid] = cluster
        for path in cluster.get("members", []):
            pages.setdefault(path, {}).update({"sector": cid})
        pillar = cluster.get("pillar")
        if pillar:
            pages.setdefault(pillar, {}).update({"sector": cid})
    for item in obj.get("pages", []):
        path = item.get("path") or item.get("id") or item.get("url")
        if isinstance(path, str):
            path = site_path(path) or path.lstrip("/")
            pages.setdefault(path, {}).update(
                {
                    "title": str(item.get("title", "")),
                    "description": str(item.get("description", "")),
                    "sector": str(item.get("cluster", item.get("sector", ""))),
                }
            )
    return pages, clusters


def merge_observations(
    github_pages: dict[str, ParsedPage],
    sitemap_set: set[str],
    dom_pages: dict[str, ParsedPage],
    declared_pages: dict[str, dict[str, str]],
    crawl_time: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(set(github_pages) | sitemap_set | set(dom_pages))
    paths = paths[:MAX_PAGES]

    node_rows: list[dict[str, Any]] = []
    edge_obs: dict[tuple[str, str], dict[str, Any]] = {}

    for path in paths:
        sources: list[str] = []
        evidence: list[dict[str, Any]] = []
        candidates = []
        if path in github_pages:
            sources.append("github_api")
            candidates.append(("github_api", github_pages[path]))
        if path in sitemap_set:
            sources.append("sitemap")
        if path in dom_pages:
            sources.append("rendered_dom")
            candidates.append(("rendered_dom", dom_pages[path]))

        title = next((p.title for _s, p in candidates if p.title), "")
        description = next((p.description for _s, p in candidates if p.description), "")
        if path in declared_pages:
            title = title or declared_pages[path].get("title", "")
            description = description or declared_pages[path].get("description", "")
        if not title:
            title = Path(path).stem.replace("-", " ").replace("_", " ").title()

        content_hash_source = github_pages.get(path) or dom_pages.get(path)
        content_hash = content_hash_source.content_hash if content_hash_source else ""
        word_count = content_hash_source.word_count if content_hash_source else 0

        node = {
            "id": path,
            "title": title[:500],
            "url": f"{SITE_ROOT}/{path}",
            "cluster": "",  # filled after Louvain
            "sector": declared_pages.get(path, {}).get("sector", "") or safe_intent_label(path),
            "page_type": "home" if path == "index.html" else safe_intent_label(path),
            "content_hash": content_hash,
            "first_seen": crawl_time,
            "last_verified": crawl_time,
            "inbound_link_count": 0,
            "outbound_link_count": 0,
            "pagerank_score": 0.0,
            "betweenness_centrality": 0.0,
            "word_count": word_count,
            "provenance_source": "+".join(sources) if sources else "unobserved",
            "confidence_score": confidence_for_sources(len(sources)),
            "provenance": [
                {
                    "source": source,
                    "observed_at": crawl_time,
                    "url": (
                        f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_REF}"
                        if source == "github_api"
                        else SITE_SITEMAP
                        if source == "sitemap"
                        else f"{SITE_ROOT}/{path}?skipboot=1"
                    ),
                    "status": "observed",
                }
                for source in sources
            ],
        }
        node["record_hash"] = record_hash(node, "record_hash")
        node_rows.append(node)

        for source_name, parsed in candidates:
            for target_url, link_type, anchor in parsed.links:
                target_path = site_path(target_url)
                if not target_path or target_path == path:
                    continue
                key = (path, target_path)
                obs = edge_obs.setdefault(
                    key,
                    {
                        "sources": set(),
                        "link_types": collections.Counter(),
                        "anchors": collections.Counter(),
                        "first_observed": crawl_time,
                        "last_confirmed": crawl_time,
                    },
                )
                obs["sources"].add(source_name)
                obs["link_types"][link_type] += 1
                if anchor:
                    obs["anchors"][anchor] += 1

    known = {n["id"] for n in node_rows}
    edges: list[dict[str, Any]] = []
    for (source, target), obs in sorted(edge_obs.items()):
        if target not in known:
            continue
        source_count = len(obs["sources"])
        weight = float(source_count)
        if source_count == 1:
            weight = 0.5
        link_type = obs["link_types"].most_common(1)[0][0] if obs["link_types"] else "internal"
        anchor = obs["anchors"].most_common(1)[0][0] if obs["anchors"] else ""
        edge = {
            "source": source,
            "target": target,
            "link_type": link_type,
            "weight": weight,
            "discovered_via": "+".join(sorted(obs["sources"])),
            "first_observed": obs["first_observed"],
            "last_confirmed": obs["last_confirmed"],
            "anchor": anchor,
            "confidence_score": confidence_for_sources(source_count),
            "provenance": [
                {
                    "source": source_name,
                    "observed_at": crawl_time,
                    "detail": "same internal edge observed in this source",
                }
                for source_name in sorted(obs["sources"])
            ],
        }
        edge["edge_hash"] = record_hash(edge, "edge_hash")
        edges.append(edge)

    by_id = {n["id"]: n for n in node_rows}
    outbound = collections.Counter(e["source"] for e in edges)
    inbound = collections.Counter(e["target"] for e in edges)
    for node in node_rows:
        node["inbound_link_count"] = inbound[node["id"]]
        node["outbound_link_count"] = outbound[node["id"]]
        node["record_hash"] = record_hash(node, "record_hash")

    stats = {
        "nodes_observed": len(node_rows),
        "edges_observed": len(edges),
        "single_source_nodes": sum(n["confidence_score"] == 0.55 for n in node_rows),
        "single_source_edges": sum(e["confidence_score"] == 0.55 for e in edges),
        "corroborated_nodes": sum(n["confidence_score"] >= 0.85 for n in node_rows),
        "corroborated_edges": sum(e["confidence_score"] >= 0.85 for e in edges),
    }
    return node_rows, edges, stats


def compute_graph_analytics(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    node_ids = [n["id"] for n in nodes]
    graph = nx.DiGraph()
    graph.add_nodes_from(node_ids)
    for edge in edges:
        graph.add_edge(
            edge["source"],
            edge["target"],
            weight=float(edge["weight"]),
            distance=1.0 / max(float(edge["weight"]), 0.25),
        )

    if len(graph):
        pagerank = nx.pagerank(graph, alpha=0.85, weight="weight")
        betweenness = nx.betweenness_centrality(graph, normalized=True, weight="distance")
    else:
        pagerank, betweenness = {}, {}

    undirected = graph.to_undirected()
    if len(undirected) and undirected.number_of_edges():
        communities = nx.community.louvain_communities(
            undirected,
            weight="weight",
            resolution=1.0,
            seed=LOUVAIN_SEED,
        )
        modularity = nx.community.modularity(undirected, communities, weight="weight")
    else:
        communities = [{node} for node in sorted(undirected.nodes())]
        modularity = 0.0

    communities = sorted(
        communities,
        key=lambda group: (-len(group), min(group) if group else ""),
    )
    node_to_cluster: dict[str, str] = {}
    cluster_rows: list[dict[str, Any]] = []

    # Build a clean declared-sector name table from observed node sector labels.
    sector_names: dict[str, str] = {}
    for n in nodes:
        sector = str(n.get("sector") or "")
        if sector:
            sector_names.setdefault(sector, sector.replace("-", " ").title())

    for idx, community in enumerate(communities, start=1):
        cid = f"community-{idx:02d}"
        for node_id in community:
            node_to_cluster[node_id] = cid
        internal = undirected.subgraph(community)
        cohesion = nx.density(internal) if len(community) > 1 else 1.0
        hub = max(community, key=lambda node: (pagerank.get(node, 0.0), -len(node), node))
        counts = collections.Counter(
            str(next((n["sector"] for n in nodes if n["id"] == node_id), "")) for node_id in community
        )
        dominant_sector = counts.most_common(1)[0][0] if counts else ""
        name = (
            f"Community {idx:02d} · {sector_names.get(dominant_sector, dominant_sector or 'Unclassified')}"
        )
        cluster = {
            "id": cid,
            "name": name,
            "sector": dominant_sector,
            "node_ids": sorted(community),
            "hub_node_id": hub,
            "modularity_score": round(float(modularity), 12),
            "cohesion_index": round(float(cohesion), 12),
        }
        cluster["record_hash"] = record_hash(cluster, "record_hash")
        cluster_rows.append(cluster)

    max_pr = max(pagerank.values(), default=0.0)
    for node in nodes:
        node["cluster"] = node_to_cluster.get(node["id"], "")
        node["pagerank_score"] = round(float(pagerank.get(node["id"], 0.0)), 12)
        node["betweenness_centrality"] = round(float(betweenness.get(node["id"], 0.0)), 12)
        node["pagerank_normalized"] = (
            round(float(pagerank.get(node["id"], 0.0) / max_pr), 12) if max_pr else 0.0
        )
        node["record_hash"] = record_hash(node, "record_hash")
    for edge in edges:
        edge["record_hash"] = record_hash(edge, "record_hash")
        edge["edge_hash"] = edge["record_hash"]

    analytics = {
        "libraries": {
            "networkx": nx.__version__,
        },
        "algorithms": {
            "pagerank": "networkx.pagerank(alpha=0.85, weight='weight')",
            "betweenness": "networkx.betweenness_centrality(normalized=True, weight='distance')",
            "community_detection": "networkx.community.louvain_communities(weight='weight', seed=42)",
            "modularity": "networkx.community.modularity(weight='weight')",
            "cohesion": "networkx.density",
        },
        "node_count": len(graph),
        "edge_count": graph.number_of_edges(),
        "community_count": len(community_rows := cluster_rows),
        "global_modularity": round(float(modularity), 12),
        "top_pagerank": sorted(
            (
                {"id": node, "score": round(score, 12)}
                for node, score in pagerank.items()
            ),
            key=lambda x: (-x["score"], x["id"]),
        )[:20],
        "top_betweenness": sorted(
            (
                {"id": node, "score": round(score, 12)}
                for node, score in betweenness.items()
            ),
            key=lambda x: (-x["score"], x["id"]),
        )[:20],
    }
    return nodes, edges, analytics


def diagnostics(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    source_evidence: list[SourceEvidence],
) -> dict[str, Any]:
    inbound = collections.Counter(e["target"] for e in edges)
    orphans = [
        {
            "node_id": n["id"],
            "title": n["title"],
            "sources": n["provenance_source"],
            "evidence": n["provenance"],
        }
        for n in nodes
        if n["id"] != "index.html" and inbound[n["id"]] == 0
    ]

    chokepoints = sorted(
        [
            {
                "node_id": n["id"],
                "title": n["title"],
                "betweenness_centrality": n["betweenness_centrality"],
                "pagerank_score": n["pagerank_score"],
                "evidence": n["provenance"],
            }
            for n in nodes
            if n["betweenness_centrality"] > 0
        ],
        key=lambda item: (-item["betweenness_centrality"], -item["pagerank_score"], item["node_id"]),
    )[:25]

    low_nodes = sorted(
        [
            {
                "node_id": n["id"],
                "title": n["title"],
                "confidence_score": n["confidence_score"],
                "provenance_source": n["provenance_source"],
                "evidence": n["provenance"],
            }
            for n in nodes
            if n["confidence_score"] < 0.85
        ],
        key=lambda item: (item["confidence_score"], item["node_id"]),
    )
    low_edges = sorted(
        [
            {
                "source": e["source"],
                "target": e["target"],
                "confidence_score": e["confidence_score"],
                "discovered_via": e["discovered_via"],
                "edge_hash": e["edge_hash"],
                "evidence": e["provenance"],
            }
            for e in edges
            if e["confidence_score"] < 0.85
        ],
        key=lambda item: (item["confidence_score"], item["source"], item["target"]),
    )

    # Declared-sector vs detected-community divergence.
    community_membership = {
        node_id: c["id"] for c in clusters for node_id in c["node_ids"]
    }
    divergence: list[dict[str, Any]] = []
    sectors = sorted({str(n.get("sector") or "") for n in nodes if n.get("sector")})
    for sector in sectors:
        members = [n["id"] for n in nodes if n.get("sector") == sector]
        counts = collections.Counter(community_membership.get(node_id, "") for node_id in members)
        if not members:
            continue
        dominant_community, dominant_count = counts.most_common(1)[0] if counts else ("", 0)
        purity = dominant_count / len(members) if members else 0.0
        divergence.append(
            {
                "sector": sector,
                "node_count": len(members),
                "dominant_detected_community": dominant_community,
                "dominant_share": round(purity, 6),
                "divergence_index": round(1.0 - purity, 6),
                "detected_community_counts": dict(sorted(counts.items())),
                "evidence": "NetworkX Louvain partition compared with declared site sector.",
            }
        )
    divergence.sort(key=lambda x: (-x["divergence_index"], x["sector"]))

    # Cross-cluster bridge deficit: sector graph connectivity, not direct-link count.
    sector_graph = nx.Graph()
    sector_graph.add_nodes_from(sectors)
    for edge in edges:
        left = next((n["sector"] for n in nodes if n["id"] == edge["source"]), "")
        right = next((n["sector"] for n in nodes if n["id"] == edge["target"]), "")
        if left and right and left != right:
            sector_graph.add_edge(left, right)
    deficits: list[dict[str, str]] = []
    for i, left in enumerate(sectors):
        for right in sectors[i + 1 :]:
            if left == right:
                continue
            if not nx.has_path(sector_graph, left, right):
                deficits.append({"sector_a": left, "sector_b": right})
    source_status = [s.as_dict() for s in source_evidence]

    return {
        "authority_gap_report": {
            "orphaned_pages": orphans,
            "structural_chokepoints": chokepoints,
            "cluster_divergence": divergence,
            "low_confidence_nodes": low_nodes,
            "low_confidence_edges": low_edges,
            "cross_cluster_bridge_deficit": deficits,
        },
        "source_status": source_status,
        "summary": {
            "orphan_count": len(orphans),
            "chokepoint_count": len(chokepoints),
            "cluster_divergence_count": sum(1 for d in divergence if d["divergence_index"] > 0),
            "low_confidence_node_count": len(low_nodes),
            "low_confidence_edge_count": len(low_edges),
            "cross_cluster_bridge_deficit_count": len(deficits),
        },
    }


def make_snapshot(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    analytics: dict[str, Any],
    diagnostics_obj: dict[str, Any],
    source_evidence: list[SourceEvidence],
    commit_sha: str,
    tree_sha: str,
    generated_at: str,
    previous_snapshot_hash: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0",
        "generator": "tools/site_intelligence_graph.py",
        "generated_at": generated_at,
        "snapshot_id": generated_at.replace(":", "").replace("-", "").replace("Z", "Z"),
        "repo_baseline": {
            "repository": GITHUB_REPO,
            "branch": GITHUB_REF,
            "commit_sha": commit_sha,
            "tree_sha": tree_sha,
            "immutable": True,
        },
        "config": {
            "site_root": SITE_ROOT,
            "sitemap": SITE_SITEMAP,
            "crawler_user_agent": USER_AGENT,
            "max_pages": MAX_PAGES,
            "max_body_bytes": MAX_BODY_BYTES,
            "max_links_per_page": MAX_LINKS_PER_PAGE,
            "min_delay_seconds": RATE_DELAY,
            "rendered_dom_enabled": PLAYWRIGHT_ENABLED,
        },
        "sources": [s.as_dict() for s in source_evidence],
        "nodes": sorted(nodes, key=lambda n: n["id"]),
        "edges": sorted(edges, key=lambda e: (e["source"], e["target"])),
        "clusters": sorted(clusters, key=lambda c: c["id"]),
        "analytics": analytics,
        "diagnostics": diagnostics_obj,
    }
    payload_hash = sha256_text(canonical_json(payload))
    snapshot_hash = sha256_text(previous_snapshot_hash + canonical_json(payload))
    payload["integrity"] = {
        "algorithm": "SHA-256",
        "canonicalization": "deterministic sorted JSON; floats rendered as compact decimal strings in hash view",
        "previous_snapshot_hash": previous_snapshot_hash,
        "payload_hash": payload_hash,
        "snapshot_hash": snapshot_hash,
        "tamper_detection": "mutating any hashed payload field changes the computed snapshot_hash",
    }
    return payload


def latest_previous_hash() -> str:
    if not LATEST_PATH.is_file():
        return ""
    try:
        obj = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
        return str(obj.get("integrity", {}).get("snapshot_hash", ""))
    except Exception:
        return ""


def append_audit(
    snapshot: dict[str, Any],
    previous_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous_audit_hash = ""
    if AUDIT_PATH.is_file():
        try:
            lines = [line for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                previous_audit_hash = str(json.loads(lines[-1]).get("audit_hash", ""))
        except Exception:
            previous_audit_hash = ""

    previous_snapshot = previous_snapshot or {}
    current_nodes = {str(n["id"]) for n in snapshot.get("nodes", [])}
    current_edges = {(str(e["source"]), str(e["target"])) for e in snapshot.get("edges", [])}
    prior_nodes = {str(n["id"]) for n in previous_snapshot.get("nodes", [])}
    prior_edges = {(str(e["source"]), str(e["target"])) for e in previous_snapshot.get("edges", [])}

    entry = {
        "timestamp": snapshot["generated_at"],
        "snapshot_id": snapshot["snapshot_id"],
        "source_status": snapshot["sources"],
        "node_delta": {
            "added": sorted(current_nodes - prior_nodes),
            "removed": sorted(prior_nodes - current_nodes),
            "added_count": len(current_nodes - prior_nodes),
            "removed_count": len(prior_nodes - current_nodes),
        },
        "edge_delta": {
            "added": [list(pair) for pair in sorted(current_edges - prior_edges)],
            "removed": [list(pair) for pair in sorted(prior_edges - current_edges)],
            "added_count": len(current_edges - prior_edges),
            "removed_count": len(prior_edges - current_edges),
        },
        "anomaly_flags": {
            "orphaned_pages": snapshot["diagnostics"]["summary"]["orphan_count"],
            "low_confidence_nodes": snapshot["diagnostics"]["summary"]["low_confidence_node_count"],
            "low_confidence_edges": snapshot["diagnostics"]["summary"]["low_confidence_edge_count"],
            "cluster_divergence": snapshot["diagnostics"]["summary"]["cluster_divergence_count"],
            "bridge_deficit": snapshot["diagnostics"]["summary"]["cross_cluster_bridge_deficit_count"],
        },
        "previous_audit_hash": previous_audit_hash,
    }
    entry["audit_hash"] = record_hash(entry, "audit_hash")
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return entry


def write_snapshot(snapshot: dict[str, Any]) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = snapshot["snapshot_id"]
    versioned = SNAPSHOT_DIR / f"site_graph_v{stamp}.json"
    text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    versioned.write_text(text, encoding="utf-8")
    LATEST_PATH.write_text(text, encoding="utf-8")

    index: list[dict[str, Any]] = []
    if INDEX_PATH.is_file():
        try:
            existing = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            index = list(existing.get("snapshots", []))
        except Exception:
            index = []
    index = [item for item in index if item.get("snapshot_id") != stamp]
    index.append(
        {
            "snapshot_id": stamp,
            "generated_at": snapshot["generated_at"],
            "file": f"site_graph_v{stamp}.json",
            "snapshot_hash": snapshot["integrity"]["snapshot_hash"],
            "node_count": len(snapshot["nodes"]),
            "edge_count": len(snapshot["edges"]),
        }
    )
    index.sort(key=lambda x: x["generated_at"], reverse=True)
    INDEX_PATH.write_text(
        json.dumps(
            {"schema_version": "1.0", "updated_at": utc_now(), "snapshots": index[:90]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return versioned, LATEST_PATH


def verify_snapshot(obj: dict[str, Any], expected_previous: str | None = None) -> list[str]:
    errors: list[str] = []
    integrity = obj.get("integrity", {})
    stored_hash = str(integrity.get("snapshot_hash", ""))
    previous = str(integrity.get("previous_snapshot_hash", ""))
    if expected_previous is not None and previous != expected_previous:
        errors.append(
            f"{obj.get('snapshot_id')}: previous snapshot hash mismatch: expected {expected_previous}, found {previous}"
        )

    payload = dict(obj)
    payload.pop("integrity", None)
    actual_payload_hash = sha256_text(canonical_json(payload))
    if actual_payload_hash != integrity.get("payload_hash"):
        errors.append(f"{obj.get('snapshot_id')}: payload_hash mismatch")

    actual_snapshot_hash = sha256_text(previous + canonical_json(payload))
    if actual_snapshot_hash != stored_hash:
        errors.append(f"{obj.get('snapshot_id')}: snapshot_hash mismatch")

    for field, rows in (
        ("nodes", obj.get("nodes", [])),
        ("edges", obj.get("edges", [])),
        ("clusters", obj.get("clusters", [])),
    ):
        hash_field = "edge_hash" if field == "edges" else "record_hash"
        for row in rows:
            expected = row.get(hash_field)
            actual = record_hash(row, hash_field)
            if expected != actual:
                errors.append(
                    f"{obj.get('snapshot_id')}: {field} record hash mismatch: {row.get('id') or row.get('source')}"
                )
                break
    return errors


def verify_audit() -> list[str]:
    if not AUDIT_PATH.is_file():
        return []
    errors: list[str] = []
    previous = ""
    for line_no, line in enumerate(AUDIT_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"audit line {line_no}: invalid JSON: {exc}")
            continue
        if obj.get("previous_audit_hash", "") != previous:
            errors.append(f"audit line {line_no}: previous hash mismatch")
        expected = record_hash(obj, "audit_hash")
        if obj.get("audit_hash") != expected:
            errors.append(f"audit line {line_no}: audit hash mismatch")
        previous = str(obj.get("audit_hash", ""))
    return errors


def verify_chain() -> int:
    files = sorted(
        SNAPSHOT_DIR.glob("site_graph_v*.json"),
        key=lambda p: p.name,
    )
    errors: list[str] = []
    previous = ""
    for path in files:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.name}: invalid JSON: {exc}")
            continue
        errors.extend(verify_snapshot(obj, expected_previous=previous))
        previous = str(obj.get("integrity", {}).get("snapshot_hash", ""))
    errors.extend(verify_audit())
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: verified {len(files)} snapshot(s) and audit chain")
    return 0


def diff_snapshots(date_a: str, date_b: str) -> dict[str, Any]:
    def resolve(selector: str) -> Path:
        candidates = sorted(SNAPSHOT_DIR.glob(f"site_graph_v*{selector}*.json"))
        if not candidates:
            candidates = sorted(OUT_DIR.glob(f"site_graph_v*{selector}*.json"))
        if not candidates:
            raise FileNotFoundError(f"snapshot selector not found: {selector}")
        return candidates[0]

    a = json.loads(resolve(date_a).read_text(encoding="utf-8"))
    b = json.loads(resolve(date_b).read_text(encoding="utf-8"))
    nodes_a = {n["id"]: n for n in a.get("nodes", [])}
    nodes_b = {n["id"]: n for n in b.get("nodes", [])}
    edges_a = {(e["source"], e["target"]): e for e in a.get("edges", [])}
    edges_b = {(e["source"], e["target"]): e for e in b.get("edges", [])}
    added_nodes = sorted(set(nodes_b) - set(nodes_a))
    removed_nodes = sorted(set(nodes_a) - set(nodes_b))
    added_edges = sorted([list(k) for k in set(edges_b) - set(edges_a)])
    removed_edges = sorted([list(k) for k in set(edges_a) - set(edges_b)])
    cluster_moves = sorted(
        [
            {
                "node_id": node_id,
                "from": nodes_a[node_id].get("cluster", ""),
                "to": nodes_b[node_id].get("cluster", ""),
            }
            for node_id in set(nodes_a) & set(nodes_b)
            if nodes_a[node_id].get("cluster") != nodes_b[node_id].get("cluster")
        ],
        key=lambda x: x["node_id"],
    )
    rank_changes = sorted(
        [
            {
                "node_id": node_id,
                "pagerank_before": nodes_a[node_id].get("pagerank_score", 0),
                "pagerank_after": nodes_b[node_id].get("pagerank_score", 0),
                "delta": round(
                    float(nodes_b[node_id].get("pagerank_score", 0))
                    - float(nodes_a[node_id].get("pagerank_score", 0)),
                    12,
                ),
            }
            for node_id in set(nodes_a) & set(nodes_b)
            if abs(
                float(nodes_b[node_id].get("pagerank_score", 0))
                - float(nodes_a[node_id].get("pagerank_score", 0))
            ) > 1e-12
        ],
        key=lambda x: (-abs(x["delta"]), x["node_id"]),
    )[:50]
    return {
        "snapshot_a": a["snapshot_id"],
        "snapshot_b": b["snapshot_id"],
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
        "cluster_moves": cluster_moves,
        "pagerank_changes": rank_changes,
    }


def run_crawl() -> int:
    started = utc_now()
    session = make_session()
    commit_sha, tree, github_pages, github_evidence = github_snapshot(session, started)
    sitemap_set, sitemap_lastmods, sitemap_evidence = sitemap_pages(session, started)
    dom_pages, dom_evidence = rendered_dom_pages(sitemap_set, started)
    declared_pages, _declared_clusters = declared_ia()

    nodes, edges, merge_stats = merge_observations(
        github_pages, sitemap_set, dom_pages, declared_pages, started
    )
    nodes, edges, analytics = compute_graph_analytics(nodes, edges)
    clusters = []
    # extract detected communities from node labels instead of recomputing them
    by_cluster: dict[str, list[str]] = collections.defaultdict(list)
    for node in nodes:
        by_cluster[node["cluster"]].append(node["id"])
    for cid, members in sorted(by_cluster.items()):
        members_set = set(members)
        hub = max(
            members,
            key=lambda node_id: (
                next(n["pagerank_score"] for n in nodes if n["id"] == node_id),
                node_id,
            ),
        )
        submod = analytics["global_modularity"]
        cohesion = 1.0 if len(members) <= 1 else nx.density(
            nx.Graph(
                [
                    (e["source"], e["target"])
                    for e in edges
                    if e["source"] in members_set and e["target"] in members_set
                ]
            ).subgraph(members_set)
        )
        sector_counts = collections.Counter(
            next((n["sector"] for n in nodes if n["id"] == node_id), "")
            for node_id in members
        )
        sector = sector_counts.most_common(1)[0][0] if sector_counts else ""
        cluster = {
            "id": cid,
            "name": f"Detected {cid}",
            "sector": sector,
            "node_ids": sorted(members),
            "hub_node_id": hub,
            "modularity_score": round(float(submod), 12),
            "cohesion_index": round(float(cohesion), 12),
        }
        cluster["record_hash"] = record_hash(cluster, "record_hash")
        clusters.append(cluster)

    sources = [github_evidence, *sitemap_evidence, *dom_evidence]
    # Explicitly retain sitemap last-modified only as evidence metadata.
    for n in nodes:
        path = n["id"]
        if path in sitemap_lastmods:
            n["sitemap_lastmod"] = sitemap_lastmods[path]
            n["record_hash"] = record_hash(n, "record_hash")

    diag = diagnostics(nodes, edges, clusters, sources)
    previous_snapshot: dict[str, Any] = {}
    if LATEST_PATH.is_file():
        try:
            previous_snapshot = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            previous_snapshot = {}
    previous = str(previous_snapshot.get("integrity", {}).get("snapshot_hash", ""))
    snapshot = make_snapshot(
        nodes,
        edges,
        clusters,
        analytics | {"merge_stats": merge_stats},
        diag,
        sources,
        commit_sha,
        str(tree.get("sha", commit_sha)),
        started,
        previous,
    )
    versioned, latest = write_snapshot(snapshot)
    append_audit(snapshot, previous_snapshot)

    print(
        json.dumps(
            {
                "snapshot": str(versioned.relative_to(ROOT)),
                "latest": str(latest.relative_to(ROOT)),
                "nodes": len(nodes),
                "edges": len(edges),
                "clusters": len(clusters),
                "snapshot_hash": snapshot["integrity"]["snapshot_hash"],
                "source_status": [
                    {"name": s.name, "status": s.status, "detail": s.detail} for s in sources
                ],
            },
            indent=2,
        )
    )
    return 0


def self_test() -> int:
    node = {"id": "a", "pagerank_score": 0.25, "confidence_score": 0.85}
    node["record_hash"] = record_hash(node, "record_hash")
    assert node["record_hash"] == record_hash(node, "record_hash")
    payload = {"nodes": [node], "edges": [], "clusters": []}
    prev = "abc123"
    obj = {
        **payload,
        "integrity": {
            "previous_snapshot_hash": prev,
            "payload_hash": sha256_text(canonical_json(payload)),
            "snapshot_hash": sha256_text(prev + canonical_json(payload)),
        },
    }
    assert not verify_snapshot(obj)
    tampered = json.loads(json.dumps(obj))
    tampered["nodes"][0]["confidence_score"] = 1.0
    assert verify_snapshot(tampered), "tamper mutation was not detected"
    assert confidence_for_sources(1) < confidence_for_sources(2) < confidence_for_sources(3)
    assert normalize_url("/index.html") == f"{SITE_ROOT}/index.html"
    assert normalize_url("javascript:alert(1)") is None
    print("PASS: hash records, snapshot chain, tamper detection, confidence and URL guards")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("crawl")
    d = sub.add_parser("diff")
    d.add_argument("date_a")
    d.add_argument("date_b")
    sub.add_parser("verify-chain")
    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "crawl":
        return run_crawl()
    if args.command == "diff":
        print(json.dumps(diff_snapshots(args.date_a, args.date_b), indent=2))
        return 0
    if args.command == "verify-chain":
        return verify_chain()
    return self_test()


if __name__ == "__main__":
    sys.exit(main())
