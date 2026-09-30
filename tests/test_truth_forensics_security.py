# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Security tests for the Truth Forensics intake and analysis boundaries.

Covers path traversal, symlinks, oversized input, SSRF-shaped URLs,
executable and archive payloads, malformed and truncated media, and
case manifests that try to reach outside their directory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from truth_forensics import case, demo, intake, vocab

ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "data" / "truth-forensics" / "demo-case.json"


# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------
def test_path_traversal_out_of_root_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("not evidence")
    with pytest.raises(intake.IntakeError, match="traversal"):
        intake.safe_open_path(root / ".." / "secret.txt", root=root)


def test_symlinks_are_refused(tmp_path: Path) -> None:
    target = tmp_path / "real.bin"
    target.write_bytes(b"x")
    link = tmp_path / "link.bin"
    os.symlink(target, link)
    with pytest.raises(intake.IntakeError, match="symbolic"):
        intake.safe_open_path(link)


def test_directories_and_missing_files_are_refused(tmp_path: Path) -> None:
    with pytest.raises(intake.IntakeError, match="regular"):
        intake.safe_open_path(tmp_path)
    with pytest.raises(intake.IntakeError, match="no such file"):
        intake.safe_open_path(tmp_path / "nope")


def test_oversized_files_are_refused(tmp_path: Path) -> None:
    big = tmp_path / "big.bin"
    big.write_bytes(b"\x00" * 2048)
    with pytest.raises(intake.IntakeError, match="limit"):
        intake.safe_open_path(big, max_bytes=1024)


def test_case_manifest_cannot_read_outside_its_directory(tmp_path: Path) -> None:
    (tmp_path / "outside.txt").write_text("private")
    base = tmp_path / "case"
    base.mkdir()
    manifest = {"evidence": [{"evidence_id": "EV-1", "file": "../outside.txt"}]}
    with pytest.raises(intake.IntakeError, match="traversal"):
        demo.load_files(manifest, base)
    manifest["evidence"][0]["file"] = "/etc/hostname"
    with pytest.raises(intake.IntakeError):
        demo.load_files(manifest, base)


def test_cli_reports_refusal_instead_of_crashing(tmp_path: Path, capsys) -> None:
    from truth_forensics.__main__ import main

    base = tmp_path / "c"
    base.mkdir()
    (tmp_path / "x.txt").write_text("x")
    spec = json.loads(CASE_PATH.read_text())
    spec["evidence"][0]["file"] = "../x.txt"
    (base / "case.json").write_text(json.dumps(spec))
    assert main(["case", str(base / "case.json")]) == 2
    assert "traversal" in capsys.readouterr().err


# --------------------------------------------------------------------------
# SSRF
# --------------------------------------------------------------------------
@pytest.mark.parametrize("url", [
    "http://example.com/a",                  # not https
    "https://localhost/admin",
    "https://127.0.0.1/",
    "https://10.0.0.5/",
    "https://192.168.1.1/",
    "https://169.254.169.254/latest/meta-data/",
    "https://[::1]/",
    "https://[::ffff:127.0.0.1]/",
    "https://0x7f000001/",
    "https://2130706433/",
    "https://0177.0.0.1/",
    "https://user:pass@example.com/",
    "https://example.com:8443/",
    "https://metadata.internal/",
    "https://printer.local/",
    "file:///etc/passwd",
    "gopher://example.com/",
    "https://exa mple.com/",
    "",
])
def test_ssrf_shaped_urls_are_not_fetchable(url: str) -> None:
    ok, reasons = intake.validate_url(url)
    assert not ok and reasons


def test_public_https_url_is_fetchable_without_resolution() -> None:
    assert intake.validate_url("https://www.clearglassinc.com/blog/") == (True, [])


# --------------------------------------------------------------------------
# hostile content
# --------------------------------------------------------------------------
@pytest.mark.parametrize("payload,mime", [
    (b"\x7fELF\x02\x01\x01" + b"\x00" * 64, "application/x-executable"),
    (b"MZ" + b"\x00" * 64, "application/x-dosexec"),
    (b"PK\x03\x04" + b"\x00" * 64, "application/zip"),
    (b"\x1f\x8b\x08" + b"\x00" * 64, "application/gzip"),
    (b"#!/bin/sh\nrm -rf /\n", "application/x-sh"),
])
def test_executables_and_archives_are_hashed_never_parsed(payload: bytes, mime: str) -> None:
    rec = intake.acquire_bytes(payload, label="x", acquired_at="t", acquired_by="u",
                               declared_name="holiday.jpg", declared_mime="image/jpeg")
    assert rec.mime_sniffed == mime and rec.processing_boundary == "HASH_ONLY"
    res = case.analyze_item(rec, payload)
    assert res["analyzer"].startswith("boundary@")
    assert [i["code"] for i in res["indicators"]] == ["CONTAINER.TYPE_MISMATCH"]


def test_filename_never_decides_the_type() -> None:
    rec = intake.acquire_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, label="x", acquired_at="t",
                               acquired_by="u", declared_name="report.pdf.exe")
    assert rec.mime_sniffed == "image/png" and rec.declared_name == "report.pdf.exe"


@pytest.mark.parametrize("eid", ["EV-A", "EV-A1", "EV-B", "EV-F", "EV-C", "EV-E", "EV-K"])
def test_truncated_and_corrupted_media_never_crash(eid: str) -> None:
    spec = json.loads(CASE_PATH.read_text())
    data = demo.load_files(spec, CASE_PATH.parent)[eid]
    for cut in (1, 5, 12, 40, 100, len(data) // 3, len(data) - 1):
        blob = data[:cut]
        rec = intake.acquire_bytes(blob, label="t", acquired_at="t", acquired_by="u")
        res = case.analyze_item(rec, blob)
        assert not res["analyzer"].startswith("failed@"), (eid, cut)
    flipped = bytearray(data)
    for i in range(0, len(flipped), max(1, len(flipped) // 50)):
        flipped[i] ^= 0x5A
    rec = intake.acquire_bytes(bytes(flipped), label="t", acquired_at="t", acquired_by="u")
    case.analyze_item(rec, bytes(flipped))


def test_analyzer_crash_is_contained(monkeypatch) -> None:
    from truth_forensics import image

    def boom(*_a, **_k):
        raise RuntimeError("synthetic analyzer defect")

    monkeypatch.setattr(image, "analyze_image", boom)
    blob = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    rec = intake.acquire_bytes(blob, label="t", acquired_at="t", acquired_by="u")
    res = case.analyze_item(rec, blob)
    assert res["indicators"][0]["code"] == "CONTAINER.ANALYZER_FAILED"
    assert res["indicators"][0]["state"] == vocab.INCONCLUSIVE
    assert "synthetic analyzer defect" not in json.dumps(res)


def test_markup_in_evidence_is_carried_as_data(tmp_path: Path) -> None:
    spec = json.loads(CASE_PATH.read_text())
    files = demo.load_files(spec, CASE_PATH.parent)
    spec["evidence"][0]["label"] = "<img src=x onerror=alert(1)>"
    spec["claim"] = "<script>alert(1)</script> shows X at 21:43"
    res = case.run_case(spec, files)
    assert res["evidence"][0]["label"] == "<img src=x onerror=alert(1)>"
    assert res["claim"]["claim"].startswith("<script>")


def test_duplicate_or_missing_evidence_ids_fail_closed() -> None:
    spec = json.loads(CASE_PATH.read_text())
    files = demo.load_files(spec, CASE_PATH.parent)
    dup = json.loads(json.dumps(spec))
    dup["evidence"][1]["evidence_id"] = dup["evidence"][0]["evidence_id"]
    with pytest.raises(case.CaseError):
        case.run_case(dup, files)
    with pytest.raises(case.CaseError):
        case.run_case({**spec, "schema": "other"}, files)
    partial = dict(files)
    partial.pop("EV-C")
    with pytest.raises(case.CaseError):
        case.run_case(spec, partial)
