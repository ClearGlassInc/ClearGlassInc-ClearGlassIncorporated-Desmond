# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Unit and integration tests for the ClearGlass Truth Forensics engine."""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest

from truth_forensics import (
    audio,
    bifocal,
    case,
    claims,
    correlation,
    demo,
    image,
    intake,
    provenance,
    report,
    review,
    timeline,
    video,
    vocab,
)
from truth_forensics.__main__ import main as cli
from truth_forensics.canonical import canonical_json, digest, pct, sha256_bytes
from truth_forensics.indicators import Indicator

ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "data" / "truth-forensics" / "demo-case.json"


@pytest.fixture(scope="module")
def demo_case() -> dict:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def demo_files(demo_case) -> dict[str, bytes]:
    return demo.load_files(demo_case, CASE_PATH.parent)


@pytest.fixture(scope="module")
def result(demo_case, demo_files) -> dict:
    return case.run_case(demo_case, demo_files)


@pytest.fixture(scope="module")
def reviewed(demo_case, demo_files) -> dict:
    return case.run_case(demo_case, demo_files, reviews=demo_case["suggested_reviews"])


def codes(res: dict, eid: str) -> set[str]:
    return {i["code"] for i in res["indicators"] if i["evidence_id"] == eid}


# --------------------------------------------------------------------------
# hashing and canonical form
# --------------------------------------------------------------------------
def test_sha256_matches_fips_180_vector() -> None:
    assert sha256_bytes(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")


def test_canonical_json_is_sorted_compact_and_ascii() -> None:
    assert canonical_json({"b": 1, "a": "\u00e9"}) == '{"a":"\\u00e9","b":1}'
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})


def test_pct_is_integer_half_up_and_none_for_empty() -> None:
    assert pct(1, 8) == 13 and pct(3, 4) == 75 and pct(1, 3) == 33 and pct(0, 0) is None


# --------------------------------------------------------------------------
# intake
# --------------------------------------------------------------------------
@pytest.mark.parametrize("head,mime", [
    (b"\xff\xd8\xff\xe0", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF89a", "image/gif"),
    (b"RIFF\x00\x00\x00\x00WEBP", "image/webp"),
    (b"RIFF\x00\x00\x00\x00WAVE", "audio/wav"),
    (b"\x00\x00\x00\x18ftypisom", "video/mp4"),
    (b"\x00\x00\x00\x14ftypqt  ", "video/quicktime"),
    (b"ID3\x04", "audio/mpeg"),
    (b"%PDF-1.7", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"\x7fELF\x02", "application/x-executable"),
    (b"MZ\x90\x00", "application/x-dosexec"),
    (b"#!/bin/sh\n", "application/x-sh"),
    (b'{"a": 1}', "application/json"),
    (b"plain words", "text/plain"),
    (b"\x00\x01\x02\x03", "application/octet-stream"),
])
def test_sniff_mime_uses_bytes(head: bytes, mime: str) -> None:
    assert intake.sniff_mime(head) == mime


def test_display_name_is_a_label_not_a_path() -> None:
    assert intake.display_name("../../etc/passwd") == "passwd"
    assert intake.display_name("C:\\evil\\a\x00b\x1f.png") == "ab.png"
    assert intake.display_name("..") == ""
    assert len(intake.display_name("x" * 500)) == 120


def test_acquire_records_hash_type_and_boundary() -> None:
    rec = intake.acquire_bytes(b"\x7fELF" + b"\x00" * 60, label="bin", acquired_at="t",
                               acquired_by="tester", declared_mime="image/png")
    assert rec.content_sha256 == sha256_bytes(b"\x7fELF" + b"\x00" * 60)
    assert rec.mime_sniffed == "application/x-executable"
    assert rec.processing_boundary == "HASH_ONLY"
    assert intake.declared_mime_indicator(rec).code == "CONTAINER.TYPE_MISMATCH"


def test_acquire_refuses_missing_custody_fields() -> None:
    with pytest.raises(intake.IntakeError):
        intake.acquire_bytes(b"x", label="a", acquired_at="t", acquired_by=" ")
    with pytest.raises(intake.IntakeError):
        intake.acquire_bytes(b"x", label="a", acquired_at="t", acquired_by="u",
                             object_kind=vocab.DERIVATIVE)


def test_url_reference_is_recorded_not_fetched() -> None:
    rec, notes = intake.acquire_url_reference("http://127.0.0.1/admin", label="u",
                                              acquired_at="t", acquired_by="u")
    assert rec.processing_boundary == "REFERENCE_ONLY"
    assert rec.provenance_state == vocab.PROVENANCE_GAP
    assert any("not fetched" in n for n in notes)
    assert any("not fetchable" in n for n in notes)


def test_evidence_records_are_immutable() -> None:
    rec = intake.acquire_bytes(b"abc", label="a", acquired_at="t", acquired_by="u")
    with pytest.raises(Exception):
        rec.content_sha256 = "0" * 64  # type: ignore[misc]


# --------------------------------------------------------------------------
# provenance
# --------------------------------------------------------------------------
def _ledger() -> provenance.ProvenanceLedger:
    led = provenance.ProvenanceLedger()
    orig = intake.acquire_bytes(b"orig", label="o", acquired_at="t1", acquired_by="u",
                                evidence_id="EV-1")
    der = intake.acquire_bytes(b"deriv", label="d", acquired_at="t2", acquired_by="u",
                               evidence_id="EV-2", object_kind=vocab.DERIVATIVE,
                               parent_id="EV-1", transformation="crop")
    led.acquired(orig)
    led.acquired(der)
    led.derived(der, parent_sha256=orig.content_sha256)
    return led


def test_ledger_chain_verifies_and_tracks_lineage() -> None:
    led = _ledger()
    assert led.verify() == (True, None)
    assert led.lineage("EV-2") == ["EV-2", "EV-1"]
    assert provenance.verify_jsonl(led.to_jsonl()) == (True, None)


def test_ledger_detects_tampering() -> None:
    lines = _ledger().to_jsonl().splitlines()
    rec = json.loads(lines[1])
    rec["detail"]["content_sha256"] = "0" * 64
    lines[1] = json.dumps(rec)
    assert provenance.verify_jsonl("\n".join(lines)) == (False, 2)


def test_ledger_rejects_unknown_events_and_anonymous_actors() -> None:
    led = provenance.ProvenanceLedger()
    with pytest.raises(ValueError):
        led.append("EDITED", "EV-1", actor="u", at="t")
    with pytest.raises(ValueError):
        led.append("ACQUIRED", "EV-1", actor="", at="t")


# --------------------------------------------------------------------------
# indicators
# --------------------------------------------------------------------------
def test_indicator_must_explain_itself() -> None:
    base = dict(code="X.Y", category="METADATA", title="t", evidence="e", method="m",
                confidence="LOW", limitation="l", alternatives=("a",),
                state=vocab.REVIEW_REQUIRED, analyzer="x@1")
    Indicator(**base)
    for field, bad in (("limitation", " "), ("alternatives", ()), ("confidence", "CERTAIN"),
                       ("state", "FAKE"), ("category", "MAGIC")):
        with pytest.raises(ValueError):
            Indicator(**{**base, field: bad})


# --------------------------------------------------------------------------
# image
# --------------------------------------------------------------------------
def _dqt(quality: int) -> bytes:
    scale = 5000 // quality if quality < 50 else 200 - 2 * quality
    natural = [max(1, min(255, (v * scale + 50) // 100)) for v in image.IJG_LUMA]
    zig = [natural[image.ZIGZAG[k]] for k in range(64)]
    return b"\x00" + bytes(zig)


def _seg(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


def make_jpeg(software: str = "", trailing: bytes = b"", c2pa: bool = False,
              exif_dims: tuple[int, int] | None = None) -> bytes:
    tiff_fields = []
    if software:
        tiff_fields.append((0x0131, software))
    tiff_fields += [(0x0132, "2026:01:02 10:00:00")]
    tiff = demo._exif(tiff_fields, [(0x9003, "2026:01:01 09:00:00")], exif_dims or (64, 48))
    out = b"\xff\xd8" + _seg(0xE1, b"Exif\x00\x00" + tiff) + _seg(0xDB, _dqt(90))
    if c2pa:
        out += _seg(0xEB, b"JP\x00\x00jumbc2pa manifest")
    out += _seg(0xC0, struct.pack(">BHHB", 8, 48, 64, 3) + b"\x01\x11\x00\x02\x11\x01\x03\x11\x01")
    out += _seg(0xDA, b"\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00")
    out += b"\x12\x34\xff\x00\x56\xff\xd0\x78"  # entropy data with stuffing and a restart
    return out + b"\xff\xd9" + trailing


def test_jpeg_structure_exif_and_quality() -> None:
    info = image.parse_jpeg(make_jpeg())
    assert info["parse_error"] == ""
    assert info["frames"][0]["width"] == 64 and info["frames"][0]["height"] == 48
    assert info["exif"]["DateTimeOriginal"] == "2026:01:01 09:00:00"
    assert image.ijg_quality(info["quant_tables"]["0"]) == {
        "quality": 90, "abs_deviation": 0, "exact": True}


def test_jpeg_indicators() -> None:
    res = image.analyze_image(make_jpeg("Adobe Photoshop 25.0", b"MOTION", True, (4000, 3000)),
                              "image/jpeg")
    found = {i.code for i in res["indicators"]}
    assert found == {"METADATA.EDITING_SOFTWARE", "METADATA.TIMESTAMP_MISMATCH",
                     "METADATA.DIMENSION_MISMATCH", "PROVENANCE.C2PA_MANIFEST_PRESENT",
                     "CONTAINER.TRAILING_DATA"}
    c2pa = next(i for i in res["indicators"] if i.code == "PROVENANCE.C2PA_MANIFEST_PRESENT")
    assert c2pa.state == vocab.INCONCLUSIVE and "not validated" in c2pa.title


def test_generator_name_is_a_synthetic_indicator_not_a_verdict() -> None:
    res = image.analyze_image(make_jpeg("Midjourney v6"), "image/jpeg")
    ind = next(i for i in res["indicators"] if i.code == "SYNTHETIC.GENERATOR_TAG")
    assert ind.state == vocab.REVIEW_REQUIRED and ind.confidence == "MODERATE"


def test_png_crc_mismatch_is_detected(demo_files) -> None:
    data = bytearray(demo_files["EV-B"])
    idat = data.find(b"IDAT")
    data[idat + 200] ^= 0xFF
    res = image.analyze_image(bytes(data), "image/png")
    assert "CONTAINER.CRC_MISMATCH" in {i.code for i in res["indicators"]}


def test_png_decompression_bomb_is_capped() -> None:
    raw = b"\x00" * (10 * 1024 * 1024)
    body = (struct.pack(">IIBBBBB", 4, 4, 8, 0, 0, 0, 0))
    png = b"\x89PNG\r\n\x1a\n" + demo._chunk(b"IHDR", body) + demo._chunk(
        b"IDAT", zlib.compress(raw, 9)) + demo._chunk(b"IEND", b"")
    res = image.analyze_image(png, "image/png")
    assert res["pixels"] is None
    assert any("decompression bomb" in n for n in res["not_performed"])


def test_ztxt_inflate_is_capped() -> None:
    body = (struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
    bomb = b"Comment\x00\x00" + zlib.compress(b"A" * (8 * 1024 * 1024), 9)
    png = (b"\x89PNG\r\n\x1a\n" + demo._chunk(b"IHDR", body) + demo._chunk(b"zTXt", bomb)
           + demo._chunk(b"IDAT", zlib.compress(b"\x00\x00")) + demo._chunk(b"IEND", b""))
    info = image.parse_png(png)
    assert len(info["text"]["Comment"]) <= 4000
    assert info["inflate_capped"] == ["Comment"]


def test_copy_move_found_only_in_the_edited_photo(demo_files) -> None:
    clean = image.analyze_image(demo_files["EV-B"], "image/png")
    edited = image.analyze_image(demo_files["EV-F"], "image/png")
    assert clean["pixels"]["clone_clusters"] == []
    cluster = edited["pixels"]["clone_clusters"][0]
    assert cluster["shift"] == [130, 68] and cluster["matched_blocks"] == 1073


def test_gps_is_exact_rational() -> None:
    exif = {"GPSLatitude": [[43, 1], [15, 1], [2052, 100]], "GPSLatitudeRef": "N",
            "GPSLongitude": [[79, 1], [52, 1], [1596, 100]], "GPSLongitudeRef": "W"}
    assert image.gps_decimal(exif) == "43.25570,-79.87110"


def test_exif_loops_and_overruns_are_refused() -> None:
    loop = b"II*\x00" + struct.pack("<I", 8) + struct.pack("<H", 1) + struct.pack(
        "<HHII", 0x8769, 4, 1, 8) + b"\x00\x00\x00\x00"
    with pytest.raises(image.ParseError):
        image.parse_exif(loop)
    with pytest.raises(image.ParseError):
        image.parse_exif(b"II*\x00" + struct.pack("<I", 9999))


# --------------------------------------------------------------------------
# audio
# --------------------------------------------------------------------------
def _wav(samples: list[int], bits: int = 16, channels: int = 1, rate: int = 8000,
         fmt_tag: int = 1) -> bytes:
    if fmt_tag == 3:
        data = struct.pack(f"<{len(samples)}f", *samples)
    elif bits == 8:
        data = bytes((s >> 8) + 128 for s in samples)
    elif bits == 24:
        data = b"".join(struct.pack("<i", s << 8)[:3] for s in samples)
    else:
        data = struct.pack(f"<{len(samples)}h", *samples)
    align = channels * bits // 8
    fmt = struct.pack("<HHIIHH", fmt_tag, channels, rate, rate * align, align, bits)
    body = b"WAVE" + b"fmt " + struct.pack("<I", 16) + fmt + b"data" + struct.pack(
        "<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


def test_demo_audio_findings(result) -> None:
    m = result["analyses"]["EV-C"]["metrics"]
    assert m["digital_silence"] == [[2400, 2550]]
    assert m["discontinuities"] == [5000]
    assert [s["at_ms"] for s in m["noise_floor_shifts"]] == [5000]
    assert result["analyses"]["EV-C"]["metadata"]["sample_rate"] == 8000


@pytest.mark.parametrize("bits", [8, 16, 24])
def test_pcm_widths_decode_to_one_scale(bits: int) -> None:
    samples = [0, 256, -256, 32512, -32768]
    info = audio.parse_wav(_wav(samples, bits=bits))
    decoded, _ = audio.decode_samples(_wav(samples, bits=bits), info)
    assert decoded[0] == samples


def test_float_wav_and_stereo_relation() -> None:
    data = _wav([0.5, -0.5, 0.25, -0.25], bits=32, channels=2, fmt_tag=3)
    info = audio.parse_wav(data)
    chans, _ = audio.decode_samples(data, info)
    assert chans == [[16384, 8192], [-16383, -8192]]
    assert audio.analyze_pcm([[1, 2, 3], [-1, -2, -3]], 8000)["channel_relation"] == "inverted"


def test_malformed_wav_reports_instead_of_crashing() -> None:
    bad = _wav([1, 2, 3])[:30]
    res = audio.analyze_audio(bad, "audio/wav")
    assert [i.code for i in res["indicators"]] == ["CONTAINER.PARSE_ERROR"]


# --------------------------------------------------------------------------
# video + timeline
# --------------------------------------------------------------------------
def test_demo_video_timeline_matches_the_spec_example(result) -> None:
    segs = [(s["start_ms"], s["end_ms"], s["label"]) for s in result["timelines"]["EV-A"]["segments"]]
    assert segs == [(0, 17000, "NORMAL"), (17000, 19000, "REVIEW"),
                    (19000, 42000, "SUPPORTED"), (42000, 44000, "ANOMALY")]
    assert result["timelines"]["EV-A"]["fps_x100"] == 2500


def test_video_container_metadata(result) -> None:
    meta = result["analyses"]["EV-A"]["metadata"]
    assert meta["created"] == "2026-03-14T21:43:03"
    assert [t["handler"] for t in meta["tracks"]] == ["vide", "soun"]
    assert meta["tags"]["encoder"] == "DemoCam DC-1 firmware 2.4"


def test_timeline_classifies_duplicates_and_backwards_time() -> None:
    runs = timeline.runs_from_timestamps([0, 40, 80, 80, 120, 40, 80])
    tl = timeline.build(runs, 1000)
    reasons = [s["reason"] for s in tl["segments"] if s["state"] == vocab.ANOMALY_DETECTED]
    assert "duplicate timestamp" in reasons
    assert "time runs backwards (non-monotonic)" in reasons
    assert tl["duplicates"] == 1 and tl["backwards"] == 1


def test_fragmented_and_malformed_mp4() -> None:
    frag = demo._box("ftyp", b"isom\x00\x00\x02\x00") + demo._box("moov", b"") + demo._box(
        "moof", b"")
    res = video.analyze_video(frag, "video/mp4")
    assert "CONTAINER.FRAGMENTED" in {i.code for i in res["indicators"]}
    overrun = struct.pack(">I4s", 9999, b"moov") + b"\x00" * 16
    res = video.analyze_video(overrun, "video/mp4")
    assert [i.code for i in res["indicators"]] == ["CONTAINER.PARSE_ERROR"]


def test_iso6709_location() -> None:
    assert video.iso6709("+43.2557-079.8711/") == "43.25570,-79.87110"


# --------------------------------------------------------------------------
# correlation and claims
# --------------------------------------------------------------------------
def test_time_comparison_respects_precision_and_dates() -> None:
    assert correlation.compare_time("21:43", "21:43:59", 0) == correlation.AGREES
    assert correlation.compare_time("21:43", "21:45:30", 60) == correlation.CONFLICTS
    assert correlation.compare_time("2026-03-14T21:43", "2026-03-15T21:43", 120) == \
        correlation.CONFLICTS
    assert correlation.compare_time("21:43", "not a time", 120) == correlation.NOT_COMPARABLE


def test_name_conflict_needs_same_place_type_with_different_identifier() -> None:
    assert correlation.compare_names("Dock 2", "Depot, Dock 4") == correlation.CONFLICTS
    assert correlation.compare_names("Northwind Depot", "Northwind Depot, Dock 4") == \
        correlation.AGREES
    assert correlation.compare_names("Dock 2", "Main Street") == correlation.NOT_COMPARABLE
    assert correlation.compare_event("moving Pallet 7", "forklift moves pallet 7") == \
        correlation.AGREES


def test_copies_and_derivatives_are_one_source() -> None:
    ev = [{"evidence_id": "A", "content_sha256": "1"}, {"evidence_id": "B", "content_sha256": "1"},
          {"evidence_id": "C", "content_sha256": "2", "parent_id": "A"},
          {"evidence_id": "D", "content_sha256": "3", "upstream_source": "cam"},
          {"evidence_id": "E", "content_sha256": "4", "upstream_source": "cam"},
          {"evidence_id": "F", "content_sha256": "5"}]
    g = correlation.independence_groups(ev)["membership"]
    assert g["A"] == g["B"] == g["C"]
    assert g["D"] == g["E"]
    assert len({g["A"], g["D"], g["F"]}) == 3


def test_decompose_demo_claim() -> None:
    props = claims.decompose(demo.CLAIM)
    got = [(p["dimension"], p["value"]) for p in props]
    assert got == [("source", "Video A"), ("identity", "Forklift FL-3"),
                   ("time", "2026-03-14T21:43"), ("location", "Dock 2"),
                   ("location", "Northwind Demo Depot"), ("event", "moving Pallet 7"),
                   ("provenance", ""), ("corroboration", "")]


def test_decompose_sequence_both_directions() -> None:
    a = [p for p in claims.decompose("The gate opened before the truck left") if
         p["dimension"] == "sequence"][0]
    b = [p for p in claims.decompose("The truck left after the gate opened") if
         p["dimension"] == "sequence"][0]
    assert a["value"] == ["The gate opened", "the truck left"]
    assert b["value"] == ["the gate opened", "The truck left"]


@pytest.mark.parametrize("agree,conflict,verdict", [
    (0, 0, vocab.UNVERIFIED), (0, 1, vocab.CONTRADICTED), (1, 1, vocab.INCONCLUSIVE),
    (1, 0, vocab.PARTIALLY_SUPPORTED), (2, 0, vocab.SUPPORTED)])
def test_verdict_rules(agree: int, conflict: int, verdict: str) -> None:
    assert claims.verdict_from_counts(agree, conflict) == verdict


def test_claim_is_a_conjunction() -> None:
    assert claims.combine([vocab.SUPPORTED, vocab.CONTRADICTED]) == vocab.CONTRADICTED
    assert claims.combine([vocab.SUPPORTED, vocab.INCONCLUSIVE]) == vocab.INCONCLUSIVE
    assert claims.combine([vocab.SUPPORTED, vocab.UNVERIFIED]) == vocab.PARTIALLY_SUPPORTED
    assert claims.combine([vocab.SUPPORTED, vocab.SUPPORTED]) == vocab.SUPPORTED


def test_claim_decomposition_is_bounded() -> None:
    import time
    start = time.perf_counter()
    claims.decompose("at A " * 5000 + "shows " + "B " * 5000)
    assert time.perf_counter() - start < 2


# --------------------------------------------------------------------------
# bifocal
# --------------------------------------------------------------------------
def test_bifocal_needs_two_channels_and_excludes_dependent_ones() -> None:
    one = bifocal.verify([{"kind": "PRIMARY_MEDIA", "evidence_id": "A"}], {"A": "G1"}, {}, {})
    assert one["score"] is None and one["status"] == "INSUFFICIENT_CHANNELS"
    chans = [{"kind": "PRIMARY_MEDIA", "evidence_id": "A", "time_window": "21:00:00/21:01:00"},
             {"kind": "INDEPENDENT_SENSOR", "evidence_id": "B",
              "time_window": "21:00:30/21:02:00"}]
    dep = bifocal.verify(chans, {"A": "G1", "B": "G1"}, {}, {})
    assert dep["checks"][0]["independent"] is False and dep["score"] is None
    ind = bifocal.verify(chans, {"A": "G1", "B": "G2"}, {}, {})
    assert ind["score"] == 100 and ind["disclaimer"] == vocab.BIFOCAL_DISCLAIMER


# --------------------------------------------------------------------------
# review
# --------------------------------------------------------------------------
def test_separation_of_duties_and_second_review() -> None:
    log = review.ReviewLog("alice")
    with pytest.raises(review.ReviewError):
        log.record("ACCEPT", "EV-1", "alice", "t")
    log.record("REQUEST_SECOND_REVIEW", "EV-1", "bob", "t1")
    with pytest.raises(review.ReviewError):
        log.record("ACCEPT", "EV-1", "bob", "t2")
    assert log.decision("EV-1")["state"] == "AWAITING_SECOND_REVIEW"
    log.record("ACCEPT", "EV-1", "carol", "t3")
    assert log.decision("EV-1")["state"] == "DECIDED"
    assert log.verify() == (True, None)


def test_review_log_is_append_only_and_tamper_evident() -> None:
    log = review.ReviewLog("alice")
    log.record("COMMENT", "EV-1", "bob", "t1", "first")
    log.record("REJECT", "EV-1", "bob", "t2", "second")
    log._records[0]["note"] = "rewritten"
    assert log.verify() == (False, 1)
    with pytest.raises(review.ReviewError):
        log.record("DELETE", "EV-1", "bob", "t3")


def test_final_status_rules() -> None:
    pending = {"state": "PENDING", "action": ""}
    accept = {"state": "DECIDED", "action": "ACCEPT"}
    assert review.final_status(vocab.VERIFIED, pending, False) == vocab.SUPPORTED
    assert review.final_status(vocab.VERIFIED, accept, False) == vocab.VERIFIED
    assert review.final_status(vocab.VERIFIED, {"state": "DECIDED", "action": "REJECT"},
                               False) == vocab.UNVERIFIED
    assert review.final_status(vocab.VERIFIED, {"state": "ESCALATED", "action": ""},
                               False) == vocab.INCONCLUSIVE
    assert review.final_status(vocab.VERIFIED, accept, True) == vocab.SIMULATED


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def test_report_sections_and_statement_types(reviewed) -> None:
    rep = report.build_report(reviewed)
    assert [s["title"] for s in rep["sections"]] == list(report.SECTIONS)
    kinds = {st["kind"] for s in rep["sections"] for st in s["statements"]}
    assert kinds <= set(vocab.STATEMENT_KINDS) and kinds == set(vocab.STATEMENT_KINDS)
    assert rep["reported_record"]["detail"]["report_sha256"] == rep["report_sha256"]
    assert report.build_report(reviewed) == rep


@pytest.mark.parametrize("phrase", ["This video is fake", "the image is authentic",
                                    "100% accurate", "we guarantee it", "detects all deepfakes",
                                    "proves the video is genuine", "infallible"])
def test_language_guard_catches_false_certainty(phrase: str) -> None:
    assert report.check_language(phrase)
    with pytest.raises(report.LanguageError):
        report._s("CONCLUSION", phrase)


def test_language_guard_passes_user_text_through_quoted(reviewed) -> None:
    st = report._s("OBSERVATION", "Claim examined: \u201c{claim}\u201d", claim="the video is fake")
    assert "the video is fake" in st["text"]
    md = report.render_markdown(report.build_report(reviewed))
    for word in ("is fake", "100% accurate", "guarantee"):
        assert word not in md.lower()


# --------------------------------------------------------------------------
# integration: the demonstration case
# --------------------------------------------------------------------------
def test_demo_files_are_current() -> None:
    assert demo.check() == []


def test_demo_findings_per_item(result) -> None:
    assert codes(result, "EV-A") == {"TEMPORAL.FRAME_TIMING_ANOMALY",
                                     "TEMPORAL.IRREGULAR_INTERVALS",
                                     "TEMPORAL.TRACK_DURATION_MISMATCH"}
    assert codes(result, "EV-A1") == {"METADATA.MODIFIED_AFTER_CREATION",
                                      "METADATA.EDITING_SOFTWARE"}
    assert codes(result, "EV-B") == set() and codes(result, "EV-B2") == set()
    assert codes(result, "EV-F") == {"CONTAINER.TYPE_MISMATCH", "METADATA.EDITING_SOFTWARE",
                                     "METADATA.TIMESTAMP_MISMATCH", "CONTAINER.TRAILING_DATA",
                                     "SPATIAL.COPY_MOVE"}
    assert codes(result, "EV-C") == {"AUDIO.DIGITAL_SILENCE", "AUDIO.DISCONTINUITY",
                                     "AUDIO.NOISE_FLOOR_SHIFT"}


def test_demo_independence_and_integrity(result) -> None:
    g = {e["evidence_id"]: e["group"] for e in result["evidence"]}
    assert g["EV-A"] == g["EV-A1"]
    assert g["EV-B"] == g["EV-B2"] == g["EV-F"]
    assert len(set(g.values())) == 7
    integ = {e["evidence_id"]: e["integrity_state"] for e in result["evidence"]}
    assert integ["EV-A"] == integ["EV-B"] == vocab.CRYPTOGRAPHICALLY_VERIFIED


def test_demo_claim_before_and_after_review(result, reviewed) -> None:
    assert result["claim"]["verdict"] == vocab.INCONCLUSIVE
    assert result["claim"]["state"] == vocab.CORROBORATION_CONFLICT
    assert result["claim"]["final_verdict"] == "PENDING_REVIEW"
    assert reviewed["claim"]["verdict"] == vocab.SUPPORTED
    assert reviewed["claim"]["final_verdict"] == vocab.SUPPORTED
    loc = [p for p in reviewed["claim"]["propositions"] if p["value"] == "Dock 2"][0]
    assert loc["excluded"][0]["evidence_id"] == "EV-F"


def test_demo_bifocal_and_gauges(result) -> None:
    bif = result["bifocal"]
    assert bif["score"] == 75 and bif["coverage"] == "4/4"
    assert [c["result"] for c in bif["checks"]] == ["AGREES", "AGREES", "CONFLICTS", "AGREES"]
    assert result["integrity_indicators"]["label"] == "ANALYTICAL INDICATORS"
    assert all(isinstance(v, int) for v in result["integrity_indicators"]["values"].values())


def test_demo_is_always_simulated_and_audited(result, reviewed) -> None:
    for res in (result, reviewed):
        assert {e["final_status"] for e in res["evidence"]} == {vocab.SIMULATED}
        assert res["label"] == vocab.DEMO_LABEL
        assert res["provenance"]["verified"] and res["reviews"]["verified"]
        assert res["external_ai"]["enabled"] is False
        assert len(res["ai_audit"]) == len(res["evidence"])
    assert result["job"]["state"] == "REVIEW_REQUIRED"


def test_graph_separates_fact_from_inference(result) -> None:
    edges = result["graph"]["edges"]
    assert {e["basis"] for e in edges} == {vocab.FACTUAL, vocab.INFERENCE}
    for e in edges:
        if e["type"] in ("SUPPORTS", "CONTRADICTS", "CAPTURED_BY", "OCCURRED_AT"):
            assert e["basis"] == vocab.INFERENCE, e
        if e["type"] in ("ANALYZED_BY", "CREATED"):
            assert e["basis"] == vocab.FACTUAL, e


def test_run_is_deterministic(demo_case, demo_files) -> None:
    a = case.run_case(demo_case, demo_files)
    b = case.run_case(demo_case, demo_files)
    a.pop("telemetry"), b.pop("telemetry")
    assert canonical_json(a) == canonical_json(b)
    assert "." not in "".join(str(v) for v in a["integrity_indicators"]["values"].values())


def test_telemetry_carries_ids_and_sizes_not_content(result) -> None:
    for t in result["telemetry"]:
        assert set(t) == {"stage", "evidence_id", "size_bytes", "analyzer", "duration_ms",
                          "outcome"}


def test_cli_case_and_report(capsys) -> None:
    assert cli(["case", str(CASE_PATH)]) == 0
    assert "TF-DEMO-0001" in capsys.readouterr().out
    assert cli(["case", str(CASE_PATH), "--report", "--review-demo"]) == 0
    out = capsys.readouterr().out
    assert "## 14. Audit Trail" in out and vocab.DEMO_LABEL in out
    assert cli(["demo", "--check"]) == 0


def test_report_masks_every_user_supplied_field(demo_case, demo_files) -> None:
    """Reviewer names, notes and labels are quoted, never guarded as engine text."""
    spec = json.loads(json.dumps(demo_case))
    spec["evidence"][0]["label"] = "the video is fake"
    reviews = [{"action": "COMMENT", "target": "EV-A", "reviewer": "is fake", "at": "t1",
                "note": "this is 100% accurate and guaranteed"}]
    res = case.run_case(spec, demo_files, reviews=reviews)
    md = report.render_markdown(report.build_report(res))
    assert "by is fake at t1" in md and "the video is fake" in md


def test_float_samples_outside_range_clip_instead_of_crashing() -> None:
    data = _wav([float("inf"), float("-inf"), float("nan"), 2.0], bits=32, fmt_tag=3)
    chans, _ = audio.decode_samples(data, audio.parse_wav(data))
    assert chans == [[32767, -32767, 0, 32767]]
