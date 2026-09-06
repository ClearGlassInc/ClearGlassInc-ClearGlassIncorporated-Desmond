"""PERCIVAL · PFAS — lab CSV ingester (stdlib only).

Converts a long-form lab CSV into a normalized ``Sample`` ready for
``pfas.screen``. CSV is the durable, lossless representation that every
accredited lab can emit; PDF layouts vary per provider and silent miscoding
would be the worst possible failure mode for a compliance tool — so PDF
ingestion is intentionally out of scope here. If a lab only emits PDF, the
operator workflow is *PDF → vendor export to CSV → this ingester.*

Required columns (case-insensitive, common synonyms accepted):
    analyte, value, units              (one or more)
Recognized: loq, mdl, qualifier/flag, sample_id, site_id, matrix, collected,
            lab, method

Unit conversion: values in µg/L | ug/L | ppb are converted to ng/L (×1000).
Other units are rejected (the ingester refuses to guess).

Qualifier semantics:
    "<", "ND", "U"           -> below_loq=True
    "J" / "EMPC" / "Q"       -> kept as reported (estimated; flagged in qualifier)
"""
from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from typing import Optional

from .pfas import AnalyteResult, Sample

# header synonyms (lowercase)
_SYN = {
    "analyte":      {"analyte", "parameter", "compound", "name"},
    "value":        {"value", "result", "concentration", "amount"},
    "units":        {"units", "unit"},
    "loq":          {"loq", "rl", "reporting_limit", "reporting limit"},
    "mdl":          {"mdl", "method_detection_limit"},
    "qualifier":    {"qualifier", "flag", "q"},
    "sample_id":    {"sample_id", "sampleid", "sample"},
    "site_id":      {"site_id", "siteid", "site", "location"},
    "matrix":       {"matrix", "media", "sample_type"},
    "collected":    {"collected", "sampled", "collection_date", "date_collected"},
    "lab":          {"lab", "laboratory"},
    "method":       {"method", "analysis_method"},
}

# ng/L conversion factors
_UNIT_FACTOR = {
    "ng/l": 1.0,
    "ppt": 1.0,                       # parts per trillion ≈ ng/L for water
    "µg/l": 1000.0,
    "ug/l": 1000.0,
    "ppb": 1000.0,                    # parts per billion ≈ µg/L
}


class IngestError(Exception):
    """Raised when the CSV is unusable (unknown headers, bad numbers, etc.)."""


def _resolve_headers(fieldnames: Iterable[str]) -> dict[str, str]:
    """Map our canonical field names to the actual header in the CSV."""
    found: dict[str, str] = {}
    if not fieldnames:
        raise IngestError("CSV has no header row")
    lower = {f.lower().strip(): f for f in fieldnames if f}
    for canon, syns in _SYN.items():
        for s in syns:
            if s in lower:
                found[canon] = lower[s]
                break
    for required in ("analyte", "value", "units"):
        if required not in found:
            raise IngestError(f"missing required column: {required}")
    return found


def _parse_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    t = s.strip().lstrip("<").lstrip("≤")
    if t == "" or t.upper() in {"ND", "NA", "N/A", "BDL"}:
        return None
    try:
        return float(t.replace(",", ""))
    except ValueError as exc:
        raise IngestError(f"non-numeric value: {s!r}") from exc


def _to_ngL(value: Optional[float], units: str) -> Optional[float]:
    if value is None:
        return None
    u = (units or "").strip().lower()
    if u not in _UNIT_FACTOR:
        raise IngestError(f"unsupported units: {units!r} (use ng/L, µg/L, or ppt/ppb)")
    return value * _UNIT_FACTOR[u]


def _is_below_loq(raw_value: str, qualifier: str) -> bool:
    q = (qualifier or "").strip().upper()
    if q in {"<", "ND", "U", "BDL"}:
        return True
    return raw_value.strip().startswith("<")


def ingest_csv(
    text: str,
    *,
    default_sample_id: str = "S-CSV",
    default_site_id: str = "SITE-CSV",
    default_matrix: str = "drinking_water",
    default_collected_utc: str = "1970-01-01T00:00:00Z",
) -> Sample:
    """Parse one CSV blob into a single ``Sample``.

    Sample-level metadata (sample_id / site_id / matrix / collected / lab /
    method) is taken from the FIRST row that defines it; subsequent rows must
    not disagree (an inconsistency raises ``IngestError`` — fail-closed).
    """
    if not (text or "").strip():
        raise IngestError("empty CSV input")

    reader = csv.DictReader(io.StringIO(text))
    cols = _resolve_headers(reader.fieldnames or [])

    sample_id: Optional[str] = None
    site_id: Optional[str] = None
    matrix: Optional[str] = None
    collected: Optional[str] = None
    lab: Optional[str] = None
    method: Optional[str] = None

    results: list[AnalyteResult] = []

    for row in reader:
        analyte = (row.get(cols["analyte"]) or "").strip()
        if not analyte:
            continue
        raw_val = (row.get(cols["value"]) or "").strip()
        units = (row.get(cols["units"]) or "").strip()

        value = _parse_float(raw_val)
        ngL = _to_ngL(value, units) if value is not None else 0.0
        loq_raw = row.get(cols["loq"]) if "loq" in cols else None
        loq = _parse_float(loq_raw) or 0.0
        loq_ngL = _to_ngL(loq, units) if loq else 0.0
        qualifier = (row.get(cols["qualifier"]) or "") if "qualifier" in cols else ""

        below = _is_below_loq(raw_val, qualifier) or value is None

        # sample-level metadata: first writer wins; later conflicts fail closed
        def _take(canon: str, current: Optional[str]) -> Optional[str]:
            if canon not in cols:
                return current
            v = (row.get(cols[canon]) or "").strip()
            if not v:
                return current
            if current is None:
                return v
            if v != current:
                raise IngestError(f"inconsistent {canon!r} across rows: {current!r} vs {v!r}")
            return current

        sample_id = _take("sample_id", sample_id)
        site_id = _take("site_id", site_id)
        matrix = _take("matrix", matrix)
        collected = _take("collected", collected)
        lab = _take("lab", lab)
        method = _take("method", method)

        results.append(AnalyteResult(
            analyte=analyte,
            value_ngL=0.0 if below else (ngL or 0.0),
            loq_ngL=loq_ngL or 0.0,
            below_loq=below,
            units="ng/L",
        ))

    if not results:
        raise IngestError("no analyte rows parsed")

    return Sample(
        sample_id=sample_id or default_sample_id,
        site_id=site_id or default_site_id,
        collected_utc=collected or default_collected_utc,
        matrix=matrix or default_matrix,
        results=tuple(results),
        lab=lab or "",
        method=method or "",
    )
