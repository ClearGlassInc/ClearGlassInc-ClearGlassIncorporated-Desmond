"""Tests for the PERCIVAL · PFAS text-PDF profile.

We synthesize a minimal but valid text-PDF in-test so the suite has no binary
fixtures and remains reproducible. The PDF carries a typical EPA-533-style
analyte/result/units/LOQ table; the parser must recover the rows, run them
through the CSV ingester, and produce a Sample that pfas.screen accepts.
"""
from __future__ import annotations

import pathlib
import sys
import zlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.pfas import Risk, ScreeningRequest, screen
from sentinel.pfas_pdf import PDFProfileError, ingest_pdf

REQ = ScreeningRequest(
    client_id="city-of-burlington-water",
    site_owner_ref="WO-2026-014",
    jurisdiction="ON, CA",
    purpose="annual compliance screening",
    requester_role="water_quality_lead",
)


def _make_text_pdf(lines: list[str], *, deflate: bool = True) -> bytes:
    """Build a minimal one-page text PDF. Uses a Tj per line so our extractor
    sees one literal string per row — the same shape a real lab PDF emits."""
    body_lines = ["BT", "/F1 10 Tf", "50 760 Td"]
    for i, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")
        if i > 0:
            body_lines.append("0 -14 Td")
        body_lines.append(f"({safe}) Tj")
    body_lines.append("ET")
    stream_data = ("\n".join(body_lines) + "\n").encode("latin-1")
    filt = ""
    if deflate:
        stream_data = zlib.compress(stream_data)
        filt = "/Filter /FlateDecode "

    objs: list[bytes] = []
    objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objs.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objs.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n")
    objs.append(
        f"4 0 obj\n<< /Length {len(stream_data)} {filt}>>\nstream\n".encode("latin-1")
        + stream_data + b"\nendstream\nendobj\n"
    )
    objs.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for o in objs:
        offsets.append(len(out))
        out += o
    xref_off = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode("latin-1")
    out += (f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref_off}\n%%EOF\n").encode("latin-1")
    return bytes(out)


EXCEEDANCE_TABLE = [
    "Lab: Acme Labs  Method: EPA 533",
    "Analyte Result Units LOQ",
    "PFOA 12.0 ng/L 2.0",
    "PFOS 12.0 ng/L 2.0",
    "PFHxS 10.0 ng/L 2.0",
    "PFBA <2.0 ng/L 2.0",
]

LOW_TABLE = [
    "Analyte Result Units LOQ",
    "PFOA 3.0 ng/L 2.0",
    "PFOS 4.0 ng/L 2.0",
    "PFHxA <2.0 ng/L 2.0",
]


def test_text_pdf_exceedance_round_trips_to_screen():
    sample = ingest_pdf(_make_text_pdf(EXCEEDANCE_TABLE))
    pkg = screen(REQ, sample)
    assert pkg.accepted is True
    assert pkg.finding.risk is Risk.EXCEEDANCE
    # 12 + 12 + 10 = 34 ng/L (PFBA is <LOQ -> lower bound)
    assert abs(pkg.finding.sum_25_ngL - 34.0) < 0.01
    assert "PFOA" in pkg.finding.detected_analytes
    assert "PFHxS" in pkg.finding.detected_analytes


def test_text_pdf_low_table():
    sample = ingest_pdf(_make_text_pdf(LOW_TABLE))
    pkg = screen(REQ, sample)
    assert pkg.finding.risk is Risk.LOW
    assert abs(pkg.finding.sum_25_ngL - 7.0) < 0.01


def test_uncompressed_pdf_also_parses():
    sample = ingest_pdf(_make_text_pdf(LOW_TABLE, deflate=False))
    pkg = screen(REQ, sample)
    assert pkg.accepted and pkg.finding.risk is Risk.LOW


def test_unknown_profile_rejected():
    with pytest.raises(PDFProfileError, match="unknown PDF profile"):
        ingest_pdf(_make_text_pdf(LOW_TABLE), profile="NOT_A_PROFILE")


def test_non_pdf_rejected():
    with pytest.raises(PDFProfileError, match="not a PDF"):
        ingest_pdf(b"hello world this is not a pdf")


def test_image_only_pdf_rejected_no_silent_ocr():
    """PDF with no text-bearing content stream must fail closed (no OCR)."""
    minimal = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n104\n%%EOF\n"
    )
    with pytest.raises(PDFProfileError, match="no recoverable text"):
        ingest_pdf(minimal)


def test_table_with_no_recognized_pfas_rejected():
    bogus = ["Analyte Result Units", "Caffeine 1.0 ng/L", "Aspirin 2.0 ng/L"]
    with pytest.raises(PDFProfileError, match="no PFAS result rows recognized"):
        ingest_pdf(_make_text_pdf(bogus))


def test_encrypted_pdf_rejected():
    enc = b"%PDF-1.4\n/Encrypt 1 0 R\n" + b"\x00" * 100
    with pytest.raises(PDFProfileError, match="encrypted"):
        ingest_pdf(enc)
