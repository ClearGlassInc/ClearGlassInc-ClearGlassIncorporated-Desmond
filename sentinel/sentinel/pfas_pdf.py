"""PERCIVAL · PFAS — text-PDF profile (stdlib only).

A minimal, dependency-free extractor for **text-based** lab PDFs that contain
a tabular PFAS results section (analyte / result / units / LOQ). It parses
the PDF cross-reference and content streams to recover text strings, applies
a vendor-agnostic heuristic to find the results table, and returns a list of
normalized rows the CSV ingester can consume — guaranteeing the same trust
loop as ``pfas_ingest.ingest_csv``.

DELIBERATE NON-GOALS (fail-closed, no silent miscoding):
  * **Scanned/image PDFs are rejected** — there is no OCR. Operator must
    obtain a text-PDF or CSV from the lab.
  * **Encrypted PDFs are rejected.**
  * **Vendor layouts that cannot be parsed are reported as ``PDFProfileError``**,
    not coerced into a wrong result.

Profile shipped:
  * ``EPA_533`` — common "Analyte | Result | Units | LOQ" table style used by
    EPA Method 533 reports (drinking-water PFAS). The profile recognises rows
    whose first token matches a canonical PFAS analyte and whose subsequent
    tokens parse as ``value units`` (+ optional LOQ).
"""
from __future__ import annotations

import io
import re
import zlib
from dataclasses import dataclass

from .pfas import HC_25_PFAS, Sample
from .pfas_ingest import IngestError, ingest_csv


class PDFProfileError(Exception):
    """Raised when a PDF cannot be safely parsed under this profile."""


# ---------- minimal text extraction ----------------------------------------

_TEXT_STR_RE = re.compile(rb"\(((?:\\\)|\\\(|[^()])*)\)\s*(?:T[Jj]|'|\")", re.DOTALL)
_HEX_STR_RE = re.compile(rb"<([0-9A-Fa-f\s]+)>\s*T[Jj]")


def _unescape_pdf_string(raw: bytes) -> str:
    out = bytearray()
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == 0x5C and i + 1 < len(raw):       # backslash escape
            n = raw[i + 1]
            mapping = {0x6E: 0x0A, 0x72: 0x0D, 0x74: 0x09, 0x62: 0x08,
                       0x66: 0x0C, 0x28: 0x28, 0x29: 0x29, 0x5C: 0x5C}
            if n in mapping:
                out.append(mapping[n])
                i += 2
                continue
            i += 1
            continue
        out.append(c)
        i += 1
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return out.decode("latin-1", errors="replace")


def _maybe_inflate(data: bytes) -> bytes:
    """Try to zlib-decompress; return original bytes if not a flate stream."""
    try:
        return zlib.decompress(data)
    except zlib.error:
        return data


def _extract_text(pdf_bytes: bytes) -> str:
    """Recover printable text from a text-based PDF. Fails closed on encrypted
    or image-only PDFs (no OCR)."""
    if not pdf_bytes.startswith(b"%PDF-"):
        raise PDFProfileError("not a PDF")
    if b"/Encrypt" in pdf_bytes[:8192]:
        raise PDFProfileError("encrypted PDF not supported")

    parts: list[str] = []
    cursor = 0
    while True:
        start = pdf_bytes.find(b"stream", cursor)
        if start < 0:
            break
        # advance past "stream" + optional CR/LF
        s = start + len(b"stream")
        if s < len(pdf_bytes) and pdf_bytes[s:s + 2] == b"\r\n":
            s += 2
        elif s < len(pdf_bytes) and pdf_bytes[s:s + 1] in (b"\r", b"\n"):
            s += 1
        end = pdf_bytes.find(b"endstream", s)
        if end < 0:
            break
        body = _maybe_inflate(pdf_bytes[s:end].rstrip(b"\r\n"))
        for m in _TEXT_STR_RE.finditer(body):
            parts.append(_unescape_pdf_string(m.group(1)))
        for m in _HEX_STR_RE.finditer(body):
            try:
                hexs = bytes.fromhex(m.group(1).decode("ascii").replace(" ", ""))
                parts.append(hexs.decode("utf-16-be", errors="replace")
                             if len(hexs) % 2 == 0 else hexs.decode("latin-1", errors="replace"))
            except ValueError:
                continue
        cursor = end + len(b"endstream")

    text = "\n".join(parts).strip()
    if not text:
        raise PDFProfileError("no recoverable text — likely an image/scanned PDF (OCR not supported)")
    return text


# ---------- profile: EPA Method 533-style PFAS tables ----------------------

_ANALYTE_FORMS = {
    "PFBA", "PFPEA", "PFPENA", "PFHXA", "PFHPA", "PFOA", "PFNA", "PFDA",
    "PFUNDA", "PFDODA", "PFTRDA", "PFTEDA",
    "PFBS", "PFPES", "PFHXS", "PFHPS", "PFOS", "PFNS", "PFDS",
    "PFOSA", "HFPO-DA", "GENX",
    "4:2 FTS", "6:2 FTS", "8:2 FTS",
    "N-MEFOSAA", "N-ETFOSAA",
}
# Index by upper-case stripped form so we can canonicalize quickly.
_CANON = {a.replace(" ", "").upper(): a for a in HC_25_PFAS}
_CANON.update({k.replace(" ", "").upper(): k for k in _ANALYTE_FORMS})

# A row token-pattern: ANALYTE  VALUE  UNITS  [LOQ]
# Values like "<2.0" or "ND" are kept as-is (the CSV ingester handles them).
_TOKEN_VALUE = re.compile(r"^(<?\d+(?:\.\d+)?|ND|<LOQ|U)$", re.IGNORECASE)
_TOKEN_UNITS = re.compile(r"^(ng/L|µg/L|ug/L|ppt|ppb)$", re.IGNORECASE)


@dataclass
class _ParsedRow:
    analyte: str
    value: str
    units: str
    loq: str = ""


def _find_rows(text: str) -> list[_ParsedRow]:
    """Heuristic, vendor-agnostic row scan."""
    rows: list[_ParsedRow] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        tokens = line.split(" ")
        # Try every prefix split: first 1..4 tokens form the analyte name.
        for n_name in (1, 2, 3, 4):
            if len(tokens) < n_name + 2:
                continue
            name_raw = " ".join(tokens[:n_name])
            key = name_raw.replace(" ", "").upper()
            canon = _CANON.get(key)
            if canon is None:
                continue
            rest = tokens[n_name:]
            if len(rest) < 2:
                continue
            if not _TOKEN_VALUE.match(rest[0]) or not _TOKEN_UNITS.match(rest[1]):
                continue
            loq = ""
            if len(rest) >= 3 and _TOKEN_VALUE.match(rest[2]):
                loq = rest[2]
            rows.append(_ParsedRow(canon, rest[0], rest[1], loq))
            break
    return rows


def _rows_to_csv(rows: list[_ParsedRow]) -> str:
    out = io.StringIO()
    out.write("analyte,value,units,loq,qualifier\n")
    for r in rows:
        val = r.value
        qual = ""
        if val.startswith("<"):
            qual = "<"
        elif val.upper() in {"ND", "U", "<LOQ"}:
            qual = val.upper().replace("<LOQ", "ND")
            val = ""
        # If qualifier indicates <LOQ, keep value empty so ingester marks below_loq.
        loq = r.loq if r.loq and not r.loq.startswith("<") else r.loq.lstrip("<")
        out.write(f"{r.analyte},{val},{r.units},{loq},{qual}\n")
    return out.getvalue()


def ingest_pdf(pdf_bytes: bytes, *, profile: str = "EPA_533") -> Sample:
    """Parse a text-based lab PDF under ``profile`` and return a normalized
    ``Sample``. Raises ``PDFProfileError`` if the profile cannot be applied
    (e.g. image PDF, encrypted, no recognized analyte rows)."""
    if profile != "EPA_533":
        raise PDFProfileError(f"unknown PDF profile: {profile!r}")
    text = _extract_text(pdf_bytes)
    rows = _find_rows(text)
    if not rows:
        raise PDFProfileError("no PFAS result rows recognized under EPA_533 profile")
    csv_text = _rows_to_csv(rows)
    try:
        return ingest_csv(csv_text)
    except IngestError as exc:
        raise PDFProfileError(f"normalized CSV failed ingestion: {exc}") from exc
