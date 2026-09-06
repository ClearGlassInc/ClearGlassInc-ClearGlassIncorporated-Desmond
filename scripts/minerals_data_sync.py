#!/usr/bin/env python3
"""Fetch, normalize, validate, and publish public ClearGlass critical-minerals signals.

The pipeline is intentionally fail-closed. A failed or malformed upstream response never
replaces a valid last-known-good snapshot. Only public, non-secret data is written.
"""

from __future__ import annotations

import email.utils
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "feeds" / "minerals"
LATEST = BASE / "latest"
HISTORY = BASE / "history"
MANIFEST_PATH = BASE / "manifest.json"

NRCAN_ATOM = (
    "https://api.io.canada.ca/io-server/gc/news/en/v2?"
    "dept=naturalresourcescanada&sort=publishedDate&orderBy=desc&"
    "publishedDate%3E=2021-07-23&pick=50&format=atom&"
    "atomtitle=Natural%20Resources%20Canada"
)

KEYWORDS = {
    "lithium": "lithium",
    "copper": "copper",
    "nickel": "nickel",
    "cobalt": "cobalt",
    "graphite": "graphite",
    "gallium": "gallium",
    "germanium": "germanium",
    "rare earth": "rare-earth-elements",
    "neodymium": "neodymium",
    "uranium": "uranium",
    "tungsten": "tungsten",
    "antimony": "antimony",
    "critical mineral": "critical-minerals",
    "mining": "mining",
    "mineral": "minerals",
}

POLICY_TERMS = (
    "strategy", "policy", "regulation", "regulatory", "tariff", "sanction",
    "export", "import", "permit", "funding", "investment", "partnership",
    "critical minerals", "supply chain", "trade", "consultation",
)

TRANSIENT_CODES = {429, 500, 502, 503, 504}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    try:
        if candidate.endswith("Z"):
            parsed = datetime.fromisoformat(candidate[:-1] + "+00:00")
        else:
            parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError):
            return None


def _retry_delay(headers: Any, attempt: int) -> float:
    retry_after = headers.get("Retry-After") if headers else None
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            pass
    return min(2 ** attempt, 16)


def fetch_bytes(url: str, *, timeout: int = 20, retries: int = 3) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.1",
            "User-Agent": "ClearGlassMineralsBot/1.0 (+https://www.clearglassinc.com/minerals.html)",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content_type = (response.headers.get("Content-Type") or "").lower()
                body = response.read()
                if not body:
                    raise ValueError("upstream returned an empty response")
                if "html" in content_type or body.lstrip().lower().startswith(b"<!doctype html"):
                    raise ValueError("upstream returned HTML instead of Atom/XML")
                return body
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in TRANSIENT_CODES:
                raise
            if attempt < retries - 1:
                time.sleep(_retry_delay(exc.headers, attempt))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(_retry_delay(None, attempt))
    assert last_error is not None
    raise last_error


def _entry_text(entry: ET.Element, name: str) -> str:
    node = entry.find(f"{{http://www.w3.org/2005/Atom}}{name}")
    return (node.text or "").strip() if node is not None else ""


def _entry_link(entry: ET.Element) -> str:
    ns = "{http://www.w3.org/2005/Atom}"
    for link in entry.findall(f"{ns}link"):
        href = (link.attrib.get("href") or "").strip()
        rel = (link.attrib.get("rel") or "alternate").strip()
        if href.startswith("https://") and rel in {"alternate", ""}:
            return href
    return ""


def parse_atom(body: bytes) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError(f"invalid XML: {exc}") from exc

    ns = "{http://www.w3.org/2005/Atom}"
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in root.findall(f"{ns}entry"):
        title = _entry_text(entry, "title")
        summary = _entry_text(entry, "summary") or _entry_text(entry, "content")
        published = parse_datetime(_entry_text(entry, "published"))
        updated = parse_datetime(_entry_text(entry, "updated"))
        url = _entry_link(entry)
        raw_id = _entry_text(entry, "id") or url or f"{title}|{published}"
        if not title or raw_id in seen:
            continue
        seen.add(raw_id)
        haystack = f"{title} {summary}".lower()
        affected = sorted({normalized for term, normalized in KEYWORDS.items() if term in haystack})
        if not affected:
            continue
        records.append(
            {
                "id": raw_id,
                "title": title,
                "published_at": published or updated,
                "updated_at": updated or published,
                "url": url or None,
                "source": "Natural Resources Canada / Government of Canada News",
                "affected_minerals": affected,
                "impact_category": "POLICY" if any(term in haystack for term in POLICY_TERMS) else "NEWS",
            }
        )
    return records


def validate_records(records: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    for index, record in enumerate(records):
        required = ("id", "title", "source", "affected_minerals", "impact_category")
        missing = [key for key in required if not record.get(key)]
        if missing:
            raise ValueError(f"record {index} missing required fields: {missing}")
        if record["id"] in ids:
            raise ValueError(f"duplicate record id: {record['id']}")
        ids.add(record["id"])
        if record.get("published_at") and parse_datetime(record["published_at"]) is None:
            raise ValueError(f"invalid published_at for record {record['id']}")
        url = record.get("url")
        if url and not str(url).startswith("https://"):
            raise ValueError(f"non-HTTPS URL for record {record['id']}")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json_atomic(path: Path, payload: dict[str, Any]) -> bool:
    encoded = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == encoded:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(encoded, encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8"))
    temp.replace(path)
    return True


def backup_last_known_good(path: Path, feed_id: str) -> Path | None:
    if not path.exists():
        return None
    try:
        existing = load_json(path)
        records = existing.get("records", [])
        if not isinstance(records, list):
            return None
        validate_records(records)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    HISTORY.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = HISTORY / f"{feed_id}-{stamp}.json"
    shutil.copy2(path, backup)
    return backup


def newest_record_timestamp(records: list[dict[str, Any]]) -> str | None:
    values = [record.get("updated_at") or record.get("published_at") for record in records]
    parsed = [parse_datetime(value) for value in values if value]
    parsed = [value for value in parsed if value]
    return max(parsed) if parsed else None


def status_for_feed(records: list[dict[str, Any]]) -> str:
    if not records:
        return "DAILY"
    newest = newest_record_timestamp(records)
    if not newest:
        return "DEGRADED"
    age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(newest.replace("Z", "+00:00"))).total_seconds() / 3600
    if age_hours > 72:
        return "STALE"
    if age_hours > 36:
        return "DELAYED"
    return "DAILY"


def update_manifest(feed_results: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    manifest = load_json(MANIFEST_PATH)
    feeds = manifest.get("feeds")
    if not isinstance(feeds, list):
        raise ValueError("manifest.feeds must be an array")
    for feed in feeds:
        result = feed_results.get(str(feed.get("id")))
        if not result:
            continue
        feed.update(
            {
                "retrieved_at": result.get("retrieved_at"),
                "source_updated_at": result.get("source_updated_at"),
                "status": result.get("status", "DEGRADED"),
                "record_count": result.get("record_count", 0),
                "confidence": result.get("confidence", "UNKNOWN"),
            }
        )
    statuses = {str(feed.get("status", "UNKNOWN")).upper() for feed in feeds}
    if "OFFLINE" in statuses or "DEGRADED" in statuses or "STALE" in statuses or "UNAVAILABLE" in statuses:
        overall = "DEGRADED"
    else:
        overall = "OPERATIONAL"
    manifest["generated_at"] = utc_now()
    manifest["overall_status"] = overall
    manifest["pipeline_status"] = overall
    return manifest, write_json_atomic(MANIFEST_PATH, manifest)


def publish_nrcan() -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    retrieved_at = utc_now()
    body = fetch_bytes(NRCAN_ATOM)
    records = parse_atom(body)
    validate_records(records)

    policy_records = [record for record in records if record["impact_category"] == "POLICY"]
    news_records = [record for record in records if record["impact_category"] == "NEWS"]
    results: dict[str, dict[str, Any]] = {}
    metrics = {"records_processed": len(records), "records_rejected": 0, "files_changed": 0, "fallbacks": 0}

    for feed_id, selected, schema in (
        ("policy", policy_records, "clearglass.minerals.policy/v1"),
        ("news", news_records, "clearglass.minerals.news/v1"),
    ):
        path = LATEST / f"{feed_id}.json"
        backup_last_known_good(path, feed_id)
        status = status_for_feed(selected)
        payload = {
            "schema": schema,
            "status": status,
            "retrieved_at": retrieved_at,
            "source_updated_at": newest_record_timestamp(selected),
            "source": "Natural Resources Canada / Government of Canada News",
            "records": selected,
            "message": "Validated public records filtered from the official Natural Resources Canada news feed.",
        }
        if write_json_atomic(path, payload):
            metrics["files_changed"] += 1
        results[feed_id] = {
            "retrieved_at": retrieved_at,
            "source_updated_at": payload["source_updated_at"],
            "status": status,
            "record_count": len(selected),
            "confidence": "HIGH",
        }
    return results, metrics


def preserve_on_failure(feed_ids: tuple[str, ...], error: Exception) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for feed_id in feed_ids:
        path = LATEST / f"{feed_id}.json"
        try:
            existing = load_json(path)
            records = existing.get("records", [])
            if not isinstance(records, list):
                raise ValueError("records is not an array")
            validate_records(records)
            results[feed_id] = {
                "retrieved_at": existing.get("retrieved_at"),
                "source_updated_at": existing.get("source_updated_at"),
                "status": "DEGRADED" if records else "UNAVAILABLE",
                "record_count": len(records),
                "confidence": "MEDIUM" if records else "UNKNOWN",
            }
        except Exception:
            results[feed_id] = {
                "retrieved_at": None,
                "source_updated_at": None,
                "status": "UNAVAILABLE",
                "record_count": 0,
                "confidence": "UNKNOWN",
            }
    print(f"NRCAN feed failure: {error}", file=sys.stderr)
    return results


def append_summary(lines: list[str]) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    start = time.monotonic()
    attempted = 2
    successful = 0
    failed = 0
    skipped = 0
    fallbacks = 0
    processed = 0
    rejected = 0
    files_changed = 0

    try:
        feed_results, metrics = publish_nrcan()
        successful = 2
        processed += metrics["records_processed"]
        rejected += metrics["records_rejected"]
        files_changed += metrics["files_changed"]
    except Exception as exc:
        failed = 2
        fallbacks = 2
        feed_results = preserve_on_failure(("policy", "news"), exc)

    manifest, manifest_changed = update_manifest(feed_results)
    if manifest_changed:
        files_changed += 1

    duration = time.monotonic() - start
    print(json.dumps({
        "feeds_attempted": attempted,
        "feeds_successful": successful,
        "feeds_failed": failed,
        "feeds_skipped": skipped,
        "records_processed": processed,
        "records_rejected": rejected,
        "data_changed_files": files_changed,
        "last_known_good_fallbacks": fallbacks,
        "pipeline_duration_seconds": round(duration, 3),
        "overall_status": manifest.get("overall_status"),
    }, indent=2))

    append_summary([
        "## CLEARGLASS MINERALS DATA PIPELINE",
        f"- Feeds attempted: {attempted}",
        f"- Feeds successful: {successful}",
        f"- Feeds failed: {failed}",
        f"- Feeds skipped: {skipped}",
        f"- Records processed: {processed}",
        f"- Records rejected: {rejected}",
        f"- Data changed files: {files_changed}",
        f"- Last-known-good fallbacks: {fallbacks}",
        f"- Pipeline duration: {duration:.3f}s",
        f"- Overall status: {manifest.get('overall_status', 'UNKNOWN')}",
    ])

    # A transient source outage is represented in data/manifest state and does not
    # destroy the production snapshot. Validation/manifest failures still raise.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
