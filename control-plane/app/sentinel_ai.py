"""Sentinel Core answered by Claude: read-only, governed, audited.

``POST /sentinel/ask`` (``routers/sentinel.py``) hands a visitor's question to
Claude with four read-only tools over the public site index, the same
``data/site-index.json`` the rule-guided console reads. Claude decides which
lookups to run, reads the results, and writes the answer in the house style of
``prompts/sentinel_core_system_prompt.md``. That is the whole of its autonomy:

* **L1 reflex** is the router: validation, the sensitive-data guard, the per-IP
  throttle and the daily request cap, all before any model call.
* **L2 deliberation** is the tool loop below, capped at
  ``sentinel_max_tool_rounds``; the final round offers no tools, so Claude must
  answer from what it has read.
* **L3 governance** is ``governance.score_action("sentinel_answer")`` and one
  append-only audit row per answer, holding a keyed hash of the question,
  never the question itself.

No tool writes, sends, books or changes anything, and none reaches any system
beyond the public site index, so the whole surface sits in the charter's
"allowed without approval" tier (SENTINEL_CORE_2030_SPEC.md, Phase 8).

The Anthropic SDK is imported only when a call is made, so the governance and
index code here import in the minimal CI environments without it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings

PROMPT_PATH = Path(__file__).parent / "data" / "sentinel_system_prompt.md"
#: Present in a repository checkout, absent from the Docker image.
REPO_INDEX = Path(__file__).resolve().parents[2] / "data" / "site-index.json"

MODES = ("executive", "technical", "pitch", "analytical")
MAX_QUESTION = 800
MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 2000
#: The same guard as sentinel.js: a question carrying a secret is never sent on.
SENSITIVE = re.compile(
    r"password|passcode|api[ -]?key|secret key|private key|credit card|card number|\bcvv\b|"
    r"credential|social insurance|health card",
    re.IGNORECASE,
)
#: Same-site page paths only, as in station-chat.js's siteUrl().
PAGE_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*(\.html|/)$")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class SentinelUnavailable(RuntimeError):
    """The model cannot answer right now; the console falls back to its rules."""


# ── configuration ────────────────────────────────────────────────────────────
def credentials_present() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def enabled(settings: Settings) -> bool:
    return bool(settings.sentinel_ai_enabled) and credentials_present()


def status(settings: Settings) -> dict[str, Any]:
    """What the console may say about its engine. Every field is true right now."""
    if not settings.sentinel_ai_enabled:
        reason = "disabled by configuration"
    elif not credentials_present():
        reason = "no Anthropic credential in the environment"
    else:
        reason = ""
    on = not reason
    return {
        "enabled": on,
        "engine": "claude" if on else "rule-guided",
        "model": settings.sentinel_model if on else None,
        "reason": reason or None,
        "stores": "a keyed hash of each question, never the question",
        "tools": [tool["name"] for tool in TOOLS],
    }


def system_prompt() -> str:
    """Everything below the prompt file's first ``---`` line (above it is documentation)."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return "\n".join(lines[i + 1:]).strip() + "\n"
    return text.strip() + "\n"


def question_fingerprint(question: str, settings: Settings) -> str:
    """Keyed hash for the ledger: correlates repeats without storing words."""
    key = (settings.sentinel_audit_hash_key or "clearglass-sentinel-dev-key").encode("utf-8")
    return hmac.new(key, question.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()


# ── daily request cap ────────────────────────────────────────────────────────
class DailyCap:
    """Model calls per UTC day, across every visitor, in this process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = ""
        self._used = 0

    def take(self, cap: int) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            if today != self._day:
                self._day, self._used = today, 0
            if self._used >= cap:
                return False
            self._used += 1
            return True

    def reset(self) -> None:
        with self._lock:
            self._day, self._used = "", 0


daily_cap = DailyCap()


# ── the site index Claude reads ──────────────────────────────────────────────
WEIGHTS = (("title", 6.0), ("summary", 3.5), ("path", 2.5), ("about", 1.5), ("group", 1.0))
STOP = set(
    "a an the and or of to for in on at by with from is are be it this that what which where who how why do does "
    "can show list find tell me my you your all every any page pages site clearglass about".split()
)


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", str(text or "").lower().replace("&", " and ")).strip() + " "


def _terms(query: str) -> list[str]:
    out: list[str] = []
    for word in _norm(query).split():
        if word in STOP:
            continue
        if len(word) >= 5 and word.endswith("ies"):
            word = word[:-3]
        elif len(word) >= 5 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        if word not in out:
            out.append(word)
    return out


def _hit(hay: str, term: str) -> bool:
    if len(term) > 3:
        return (" " + term) in hay
    return (" " + term + " ") in hay or (" " + term + "s ") in hay


class SiteIndex:
    """The public site graph: pages, clusters and related links. Read-only."""

    def __init__(self, data: dict) -> None:
        self.pages: dict[str, dict] = {}
        for row in data.get("pages") or []:
            path = str(row.get("path") or "")
            title = str(row.get("title") or "").strip()
            if not PAGE_PATH.match(path) or ".." in path or "//" in path or not title or path in self.pages:
                continue
            self.pages[path] = {
                "path": path,
                "title": title,
                "summary": str(row.get("summary") or ""),
                "about": str(row.get("about") or ""),
                "cluster": str(row.get("cluster") or ""),
                "hub": row.get("role") == "hub",
                "related": [r for r in row.get("related") or [] if isinstance(r, str)],
                "prev": str(row.get("prev") or ""),
                "next": str(row.get("next") or ""),
            }
        self.clusters: dict[str, dict] = {}
        for row in data.get("clusters") or []:
            cid = str(row.get("id") or "")
            if cid and str(row.get("pillar") or "") in self.pages:
                self.clusters[cid] = {
                    "id": cid,
                    "name": str(row.get("name") or cid),
                    "pillar": str(row["pillar"]),
                    "members": [m for m in row.get("members") or [] if m in self.pages],
                }
        for page in self.pages.values():
            page["group"] = self.clusters.get(page["cluster"], {}).get("name", "")
            page["hay"] = {
                "title": _norm(page["title"]), "summary": _norm(page["summary"]),
                "path": _norm(page["path"].replace(".html", "")), "about": _norm(page["about"]),
                "group": _norm(page["group"]),
            }
        if not self.pages:
            raise ValueError("site index holds no pages")

    def brief(self, path: str) -> dict:
        page = self.pages[path]
        return {"path": path, "title": page["title"], "summary": page["summary"], "cluster": page["group"]}

    def search(self, query: str, limit: int = 6) -> list[dict]:
        terms = _terms(query)
        if not terms:
            return []
        scored = []
        for page in self.pages.values():
            hits = {}
            for term in terms:
                for field_name, weight in WEIGHTS:
                    if _hit(page["hay"][field_name], term):
                        hits[term] = max(hits.get(term, 0.0), weight)
                        break
            if not hits:
                continue
            score = sum(hits.values()) * (0.4 + 0.6 * len(hits) / len(terms)) + (0.5 if page["hub"] else 0.0)
            # the same bonuses as the console: the whole phrase in the title, or
            # a title that leads with the first word asked about
            if len(terms) > 1 and (" " + " ".join(terms)) in page["hay"]["title"]:
                score += 8.0
            if page["hay"]["title"].startswith(" " + terms[0]):
                score += 1.5
            scored.append((score, page["title"], page["path"]))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [dict(self.brief(path), score=round(score, 2)) for score, _title, path in scored[: max(1, min(8, limit))]]

    def page(self, path: str) -> dict | None:
        page = self.pages.get(path)
        if not page:
            return None
        return {
            **self.brief(path),
            "description": page["about"],
            "role": "topic hub" if page["hub"] else "page",
            "related": [self.brief(p) for p in page["related"] if p in self.pages],
            "previous_in_journey": page["prev"] if page["prev"] in self.pages else None,
            "next_in_journey": page["next"] if page["next"] in self.pages else None,
        }

    def cluster_list(self) -> list[dict]:
        return [
            {"id": c["id"], "name": c["name"], "hub": c["pillar"], "pages": len(c["members"]) + 1}
            for c in self.clusters.values()
        ]

    def cluster(self, cid: str) -> dict | None:
        c = self.clusters.get(cid)
        if not c:
            return None
        return {"id": cid, "name": c["name"], "hub": self.brief(c["pillar"]),
                "members": [self.brief(p) for p in c["members"]]}


_index_lock = threading.Lock()
_index_cache: dict[str, Any] = {"at": 0.0, "index": None, "source": ""}


def load_index(settings: Settings) -> SiteIndex:
    """The site index, from a local copy when one exists, else the published site."""
    now = time.monotonic()
    with _index_lock:
        cached = _index_cache["index"]
        if cached is not None and now - _index_cache["at"] < settings.sentinel_index_ttl_seconds:
            return cached
    path = settings.sentinel_site_index_path or (str(REPO_INDEX) if REPO_INDEX.is_file() else "")
    try:
        if path:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            source = path
        else:
            import httpx

            response = httpx.get(settings.sentinel_site_index_url, timeout=8.0, follow_redirects=True)
            response.raise_for_status()
            data = response.json()
            source = settings.sentinel_site_index_url
        index = SiteIndex(data)
    except Exception as exc:  # any failure means "no index", never a guess
        if cached is not None:
            return cached                      # stale beats nothing; it is the same public site
        raise SentinelUnavailable(f"site index unavailable: {type(exc).__name__}") from exc
    with _index_lock:
        _index_cache.update(at=now, index=index, source=source)
    return index


def reset_index_cache() -> None:
    with _index_lock:
        _index_cache.update(at=0.0, index=None, source="")


# ── tools: read-only lookups over the index ──────────────────────────────────
TOOLS: list[dict] = [
    {
        "name": "search_site",
        "description": (
            "Search the public ClearGlass website by meaning-bearing words (page titles, summaries, "
            "descriptions, clusters). Returns up to `limit` pages, best first, each with its path, "
            "title, one-line summary and cluster. Use it first for any question about what "
            "ClearGlass offers or where something is on the site."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search words, e.g. 'pricing' or 'osint workflow'."},
                "limit": {"type": "integer", "description": "How many pages to return, 1 to 8."},
            },
            "required": ["query", "limit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_page",
        "description": (
            "Read one page's entry: title, summary, its own meta description, cluster, whether it is "
            "the cluster's hub, its related pages and its previous/next pages in the site journey. "
            "Pass a path exactly as search_site or another tool returned it."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "A site path such as 'pricing.html'."}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_clusters",
        "description": "List the site's topic clusters with their hub page and page counts.",
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "name": "get_cluster",
        "description": "List every page in one cluster, hub first. Pass an id from list_clusters.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"cluster_id": {"type": "string", "description": "A cluster id such as 'security'."}},
            "required": ["cluster_id"],
            "additionalProperties": False,
        },
    },
]


def run_tool(index: SiteIndex, name: str, args: Any) -> tuple[dict | list, list[str], bool]:
    """Run one lookup. Returns (result, page paths it surfaced, is_error)."""
    args = args if isinstance(args, dict) else {}
    if name == "search_site":
        try:
            limit = int(args.get("limit") or 6)
        except (TypeError, ValueError):
            limit = 6
        hits = index.search(str(args.get("query") or "")[:200], limit)
        return {"results": hits}, [h["path"] for h in hits], False
    if name == "get_page":
        path = str(args.get("path") or "")
        entry = index.page(path)
        if entry is None:
            return {"error": f"no page at {path!r}; use a path from search_site"}, [], True
        return entry, [path], False
    if name == "list_clusters":
        return {"clusters": index.cluster_list()}, [], False
    if name == "get_cluster":
        entry = index.cluster(str(args.get("cluster_id") or ""))
        if entry is None:
            return {"error": "unknown cluster id; use list_clusters"}, [], True
        return entry, [entry["hub"]["path"]] + [m["path"] for m in entry["members"]], False
    return {"error": f"unknown tool {name!r}"}, [], True


# ── the answer loop ──────────────────────────────────────────────────────────
@dataclass
class Answer:
    text: str
    mode: str
    model: str
    served_by: str
    sources: list[dict] = field(default_factory=list)
    lookups: list[str] = field(default_factory=list)
    rounds: int = 0
    stop_reason: str = ""
    refused: bool = False
    latency_ms: int = 0


def make_client():
    """The Anthropic client. Credentials come from the environment only."""
    import anthropic

    return anthropic.Anthropic(max_retries=2, timeout=90.0)


def _history(turns: list[dict] | None) -> list[dict]:
    """At most six prior turns, text only, starting with the visitor."""
    out: list[dict] = []
    for turn in (turns or [])[-MAX_HISTORY_TURNS:]:
        role, content = turn.get("role"), str(turn.get("content") or "")[:MAX_HISTORY_CHARS].strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def _pick_sources(index: SiteIndex, surfaced: list[str], read: list[str], text: str) -> list[dict]:
    """Pages the answer names; else the pages Claude opened. Same-site paths only."""
    lowered = text.lower()
    named = [p for p in dict.fromkeys(surfaced)
             if p in index.pages and (index.pages[p]["title"].lower() in lowered or p.lower() in lowered)]
    chosen = named or [p for p in dict.fromkeys(read) if p in index.pages]
    return [{"path": p, "title": index.pages[p]["title"]} for p in chosen[:5]]


def ask(
    question: str,
    *,
    settings: Settings,
    mode: str = "executive",
    page: str | None = None,
    history: list[dict] | None = None,
    client: Any = None,
) -> Answer:
    """Answer one question with Claude and the read-only site tools."""
    started = time.monotonic()
    index = load_index(settings)
    client = client or make_client()
    mode = mode if mode in MODES else "executive"
    context = f"Writing mode: {mode}."
    if page and page in index.pages:
        here = index.pages[page]
        context += f" The visitor is reading {here['title']} ({page}), in {here['group']}."
    messages: list[dict] = _history(history) + [{
        "role": "user",
        "content": [{"type": "text", "text": context}, {"type": "text", "text": question}],
    }]
    system = [{"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}]
    surfaced: list[str] = []
    read: list[str] = []
    lookups: list[str] = []
    rounds = 0
    response = None
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - the dependency is in requirements.txt
        raise SentinelUnavailable("anthropic SDK not installed") from exc
    max_rounds = max(0, settings.sentinel_max_tool_rounds)
    while True:
        rounds += 1
        last = rounds > max_rounds
        try:
            response = client.beta.messages.create(
                model=settings.sentinel_model,
                max_tokens=settings.sentinel_max_tokens,
                system=system,
                tools=TOOLS,
                # the last round offers no tools, so Claude answers from what it read
                tool_choice={"type": "none"} if last else {"type": "auto"},
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": settings.sentinel_effort},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.RateLimitError as exc:
            raise SentinelUnavailable("model rate limited") from exc
        except anthropic.APIStatusError as exc:
            raise SentinelUnavailable(f"model error {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise SentinelUnavailable("model unreachable") from exc
        if response.stop_reason == "refusal":
            break
        uses = [b for b in response.content if getattr(b, "type", "") == "tool_use"]
        if response.stop_reason != "tool_use" or not uses or last:
            break
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in uses:
            result, paths, is_error = run_tool(index, block.name, block.input)
            lookups.append(block.name)
            surfaced.extend(paths)
            if block.name == "get_page" and paths:
                read.extend(paths)
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False), "is_error": is_error})
        messages.append({"role": "user", "content": results})

    served_by = str(getattr(response, "model", "") or settings.sentinel_model)
    if response.stop_reason == "refusal":
        text = ("Sentinel can't answer that one. Ask about ClearGlass services, platforms or briefs, "
                "or reach a person through the services page.")
        return Answer(text=text, mode=mode, model=settings.sentinel_model, served_by=served_by,
                      lookups=lookups, rounds=rounds, stop_reason="refusal", refused=True,
                      latency_ms=int((time.monotonic() - started) * 1000))
    text = "".join(getattr(b, "text", "") for b in response.content if getattr(b, "type", "") == "text").strip()
    if not text:
        raise SentinelUnavailable(f"empty answer ({response.stop_reason})")
    return Answer(
        text=text, mode=mode, model=settings.sentinel_model, served_by=served_by,
        sources=_pick_sources(index, surfaced, read, text), lookups=lookups, rounds=rounds,
        stop_reason=str(response.stop_reason), latency_ms=int((time.monotonic() - started) * 1000),
    )
