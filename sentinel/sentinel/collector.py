"""PERCIVAL Agent Mesh — OSINT collector (approved public sources only).

Fetches from a registry of APPROVED, public open-source feeds and normalizes
results into ``Signal`` records (entity / source / timestamp / confidence /
summary). Network access is INJECTED (a ``Fetcher`` callable) so the collector
is testable offline and so robots.txt / ToS / rate-limit compliance is enforced
at the fetch boundary, not bypassed here.

Scope is ORGANIZATIONS / BRANDS / DOMAINS / FACILITIES / INFRASTRUCTURE /
PUBLIC INCIDENTS / VULNERABILITY INTEL — never private individuals.
"""
from __future__ import annotations

import datetime as _dt
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, Protocol

# Feeds are untrusted external XML, so prefer defusedxml (blocks entity-expansion
# "billion laughs" / external-entity attacks). It is an optional hardening dep so
# the pure-stdlib trust loop still runs without an install; stdlib ElementTree has
# no external-entity resolver, so the fallback is safe against XXE file reads.
try:
    from defusedxml.ElementTree import fromstring as _xml_fromstring
except ImportError:  # pragma: no cover - exercised only when defusedxml is absent
    from xml.etree.ElementTree import fromstring as _xml_fromstring  # nosec B314


@dataclass(frozen=True)
class OSINTSource:
    key: str
    name: str
    url: str
    domain: str                 # web|news|financial|legal|vuln|geospatial|telecom|threat
    needs_key: bool = False     # if True, a credential must be supplied at fetch time
    format: str = "rss"         # rss | json | csv | api


# 24 approved, public open-source feeds (asset/threat/org focus; no person DBs).
APPROVED_SOURCES: dict[str, OSINTSource] = {s.key: s for s in [
    OSINTSource("usgs_quakes", "USGS earthquakes", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson", "geospatial", format="json"),
    OSINTSource("nws_alerts", "NWS weather alerts", "https://api.weather.gov/alerts/active", "geospatial", format="json"),
    OSINTSource("opensky", "OpenSky aircraft (ADS-B)", "https://opensky-network.org/api/states/all", "telecom", format="json"),
    OSINTSource("exploit_db", "Exploit-DB", "https://www.exploit-db.com/", "vuln"),
    OSINTSource("nvd_cve", "NVD CVE feed", "https://services.nvd.nist.gov/rest/json/cves/2.0", "vuln", format="json"),
    OSINTSource("cisa_kev", "CISA Known Exploited Vulns", "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json", "vuln", format="json"),
    OSINTSource("cisa_advisories", "CISA advisories", "https://www.cisa.gov/cybersecurity-advisories/all.xml", "threat"),
    OSINTSource("github_advisories", "GitHub Security Advisories", "https://github.com/advisories.atom", "vuln"),
    OSINTSource("urlhaus", "abuse.ch URLhaus", "https://urlhaus.abuse.ch/downloads/csv_recent/", "threat", format="csv"),
    OSINTSource("threatfox", "abuse.ch ThreatFox", "https://threatfox.abuse.ch/export/json/recent/", "threat", format="json"),
    OSINTSource("feodo", "abuse.ch Feodo C2", "https://feodotracker.abuse.ch/downloads/ipblocklist.json", "threat", format="json"),
    OSINTSource("phishtank", "PhishTank", "https://data.phishtank.com/data/online-valid.json", "threat", format="json"),
    OSINTSource("krebs", "Krebs on Security", "https://krebsonsecurity.com/feed/", "news"),
    OSINTSource("bleeping", "BleepingComputer", "https://www.bleepingcomputer.com/feed/", "news"),
    OSINTSource("theregister_sec", "The Register · Security", "https://www.theregister.com/security/headlines.atom", "news"),
    OSINTSource("thehackernews", "The Hacker News", "https://feeds.feedburner.com/TheHackersNews", "news"),
    OSINTSource("hn", "Hacker News front page", "https://hnrss.org/frontpage", "web"),
    OSINTSource("gdelt", "GDELT events", "https://api.gdeltproject.org/api/v2/doc/doc", "news", format="api"),
    OSINTSource("sec_edgar", "SEC EDGAR filings", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&output=atom", "financial"),
    OSINTSource("opencorporates", "OpenCorporates", "https://api.opencorporates.com/v0.4/companies/search", "legal", needs_key=True, format="api"),
    OSINTSource("companies_house", "UK Companies House", "https://api.company-information.service.gov.uk/search/companies", "legal", needs_key=True, format="api"),
    OSINTSource("ofac_sdn", "OFAC sanctions (SDN)", "https://www.treasury.gov/ofac/downloads/sdn.csv", "legal", format="csv"),
    OSINTSource("rss_generic", "Generic RSS/Atom feed", "", "news"),
    OSINTSource("wikipedia", "Wikipedia (org/entity)", "https://en.wikipedia.org/w/api.php", "web", format="api"),
]}


class CollectorError(Exception):
    pass


class Fetcher(Protocol):
    def get(self, url: str, *, key: Optional[str] = None) -> str: ...


@dataclass(frozen=True)
class Signal:
    entity: str
    source: str
    title: str
    published_utc: str
    confidence: float
    summary: str
    url: str


def _norm_time(raw: str) -> str:
    raw = (raw or "").strip()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return _dt.datetime.strptime(raw, fmt).astimezone(_dt.timezone.utc).isoformat()
        except ValueError:
            continue
    return raw or _dt.datetime.now(_dt.timezone.utc).isoformat()


def _strip(s: Optional[str]) -> str:
    return (s or "").strip()


def parse_feed(xml_text: str, *, source_name: str, entity: str) -> list[Signal]:
    """Parse RSS 2.0 or Atom into Signals. Confidence is a simple relevance
    heuristic: higher when the entity term appears in the title."""
    try:
        root = _xml_fromstring(xml_text)  # nosec B314 - defusedxml when available; stdlib fallback has no external-entity resolver
    except (ET.ParseError, ValueError) as exc:
        # ValueError covers defusedxml's EntitiesForbidden / DTDForbidden, so a
        # malicious feed fails closed as a CollectorError rather than crashing.
        raise CollectorError(f"feed is not valid XML: {exc}") from exc

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item")            # RSS 2.0
    is_atom = False
    if not items:
        items = root.findall(".//atom:entry", ns)   # Atom
        is_atom = True

    out: list[Signal] = []
    ent = (entity or "").lower()
    for it in items:
        if is_atom:
            title = _strip(it.findtext("atom:title", default="", namespaces=ns))
            link_el = it.find("atom:link", ns)
            link = _strip(link_el.get("href") if link_el is not None else "")
            pub = _strip(it.findtext("atom:updated", default="", namespaces=ns)
                         or it.findtext("atom:published", default="", namespaces=ns))
            summary = _strip(it.findtext("atom:summary", default="", namespaces=ns))
        else:
            title = _strip(it.findtext("title"))
            link = _strip(it.findtext("link"))
            pub = _strip(it.findtext("pubDate"))
            summary = _strip(it.findtext("description"))
        if not title and not link:
            continue
        conf = 0.55
        if ent and ent in title.lower():
            conf += 0.25
        if ent and ent in summary.lower():
            conf += 0.10
        out.append(Signal(entity=entity, source=source_name, title=title,
                          published_utc=_norm_time(pub), confidence=round(min(conf, 0.95), 2),
                          summary=summary[:400], url=link))
    return out


class Collector:
    """Collects from approved sources via an injected fetcher."""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    def collect(self, source_key: str, entity: str, *, key: Optional[str] = None) -> list[Signal]:
        src = APPROVED_SOURCES.get(source_key)
        if src is None:
            raise CollectorError(f"source '{source_key}' is not an approved OSINT source")
        if src.needs_key and not key:
            raise CollectorError(f"source '{src.name}' requires an API key (none supplied)")
        if src.format not in ("rss",):
            # Non-feed sources are normalized by their own adapters in production;
            # the reference collector handles RSS/Atom directly.
            raise CollectorError(f"reference collector handles rss/atom only; "
                                 f"'{src.name}' is {src.format} (use its adapter)")
        text = self.fetcher.get(src.url, key=key)
        return parse_feed(text, source_name=src.name, entity=entity)


def sources_by_domain() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for s in APPROVED_SOURCES.values():
        out.setdefault(s.domain, []).append(s.key)
    return out
