# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Deterministic demonstration case.

DEMONSTRATION DATA - NOT REAL EVIDENCE. Every file is synthesised here from
fixed arithmetic: a fictional depot, a fictional forklift, no people. Nothing
depicts or accuses anyone. The MP4 files are container-only (timing tables,
no decodable frames); the PNGs are generated scenes; the WAV is generated
tones and noise.

The case is built so each subsystem has something real to find:

    EV-A   video, 25 fps, irregular intervals at 00:17-00:19, a 2 s frame gap
           at 00:42, audio track 2 s shorter than video; hash on a custody receipt
    EV-A1  declared trimmed re-encode of EV-A (editor tag, modified time)
    EV-B   photo, clean EXIF; hash on the custody receipt
    EV-B2  byte-identical copy of EV-B (one source, not two)
    EV-F   "repost" of the same scene: cloned region, editor tag, EXIF time
           mismatch, trailing bytes; an analyst reads the dock sign as 4
    EV-C   audio: exact digital silence, a splice-like step, a room-tone shift
    EV-D   dispatch log (text)
    EV-E   door-sensor window (structured record)
    EV-H   clock reference: camera clock 7 s off (tolerance 5 s)
    EV-K   custody receipt for EV-A and EV-B

    python -m truth_forensics demo --write    # regenerate data/truth-forensics/
    python -m truth_forensics demo --check    # exit 1 if the committed files differ
"""
from __future__ import annotations

import json
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

from . import vocab
from .canonical import sha256_bytes

ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / "data" / "truth-forensics" / "demo"
CASE_FILE = ROOT / "data" / "truth-forensics" / "demo-case.json"
EPOCH_1904 = 2082844800

T_CAPTURE = EPOCH_1904 + int(datetime(2026, 3, 14, 21, 43, 3, tzinfo=timezone.utc).timestamp())
T_EXPORT = EPOCH_1904 + int(datetime(2026, 3, 16, 9, 30, 0, tzinfo=timezone.utc).timestamp())
# One 1 kHz cycle at 8 kHz, amplitude 6000, as integers (no libm in the output).
BEEP = (0, 4243, 6000, 4243, 0, -4243, -6000, -4243)

W, H = 240, 160
CLAIM = ("Video A shows Forklift FL-3 moving Pallet 7 out of Dock 2 at Northwind Demo Depot "
         "at 21:43 on 14 March 2026.")


class LCG:
    """Numerical Recipes LCG: identical sequence in Python and JavaScript."""

    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.state = (1664525 * self.state + 1013904223) & 0xFFFFFFFF
        return self.state

    def between(self, lo: int, hi: int) -> int:
        return lo + self.next() % (hi - lo + 1)


# --------------------------------------------------------------------------
# PNG
# --------------------------------------------------------------------------
def _chunk(ctype: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(
        ">I", zlib.crc32(ctype + body) & 0xFFFFFFFF)


def _stored_zlib(raw: bytes) -> bytes:
    """zlib stream of stored (uncompressed) blocks: identical bytes on any zlib."""
    out = bytearray(b"\x78\x01")
    for i in range(0, len(raw), 65535):
        block = raw[i:i + 65535]
        final = 1 if i + 65535 >= len(raw) else 0
        out += bytes([final]) + struct.pack("<HH", len(block), len(block) ^ 0xFFFF) + block
    out += struct.pack(">I", zlib.adler32(raw) & 0xFFFFFFFF)
    return bytes(out)


def _exif(fields: list[tuple[int, str]], exif_fields: list[tuple[int, str]],
          dims: tuple[int, int]) -> bytes:
    """Little-endian TIFF: IFD0 (ASCII tags + Exif pointer), Exif IFD."""
    def ifd(entries: list[tuple[int, int, int, bytes]], start: int) -> tuple[bytes, bytes]:
        head = struct.pack("<H", len(entries))
        data = b""
        data_start = start + 2 + 12 * len(entries) + 4
        for tag, typ, count, value in entries:
            if len(value) <= 4:
                head += struct.pack("<HHI", tag, typ, count) + value.ljust(4, b"\x00")
            else:
                head += struct.pack("<HHII", tag, typ, count, data_start + len(data))
                data += value + (b"\x00" if len(value) % 2 else b"")
        return head + b"\x00\x00\x00\x00", data

    def ascii_entry(tag: int, text: str) -> tuple[int, int, int, bytes]:
        raw = text.encode("latin-1") + b"\x00"
        return (tag, 2, len(raw), raw)

    ifd0_entries = [ascii_entry(t, v) for t, v in fields]
    ifd0_entries.append((0x8769, 4, 1, b"\x00\x00\x00\x00"))  # patched below
    ifd0_entries.sort(key=lambda e: e[0])
    head0, data0 = ifd(ifd0_entries, 8)
    exif_offset = 8 + len(head0) + len(data0)
    ifd0_entries = [(t, ty, c, struct.pack("<I", exif_offset) if t == 0x8769 else v)
                    for t, ty, c, v in ifd0_entries]
    head0, data0 = ifd(ifd0_entries, 8)
    exif_entries = [ascii_entry(t, v) for t, v in exif_fields]
    exif_entries += [(0xA002, 4, 1, struct.pack("<I", dims[0])),
                     (0xA003, 4, 1, struct.pack("<I", dims[1]))]
    exif_entries.sort(key=lambda e: e[0])
    head1, data1 = ifd(exif_entries, exif_offset)
    return b"II*\x00" + struct.pack("<I", 8) + head0 + data0 + head1 + data1


def scene(seed: int = 7) -> list[list[tuple[int, int, int]]]:
    rng = LCG(seed)
    px = []
    for y in range(H):
        row = []
        for x in range(W):
            r, g, b = 40 + y // 4, 50 + x // 6, 70 + (x + y) // 8
            if 20 <= x < 110 and 30 <= y < 140:        # dock door
                r, g, b = r // 2 + 20, g // 2 + 25, b // 2 + 35
            if 45 <= x < 85 and 6 <= y < 24:           # dock-number sign
                r, g, b = 225, 220, 90
            if 150 <= x < 225 and 85 <= y < 140:       # forklift body
                r, g, b = 230, 130, 30
            if 60 <= x < 70 and 10 <= y < 20:          # sign glyph
                r, g, b = 30, 30, 30
            n = rng.between(-12, 12)
            row.append((max(0, min(255, r + n)), max(0, min(255, g + n)),
                        max(0, min(255, b + n))))
        px.append(row)
    return px


def png(pixels: list[list[tuple[int, int, int]]], exif: bytes, texts: dict[str, str],
        trailing: bytes = b"") -> bytes:
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b in row:
            raw += bytes((r, g, b))
    out = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    out += _chunk(b"eXIf", exif)
    for key, value in texts.items():
        out += _chunk(b"tEXt", key.encode("latin-1") + b"\x00" + value.encode("latin-1"))
    out += _chunk(b"IDAT", _stored_zlib(bytes(raw))) + _chunk(b"IEND", b"")
    return out + trailing


def photo_b() -> bytes:
    exif = _exif([(0x010F, "DemoCam"), (0x0110, "DC-1 Still"), (0x0132, "2026:03:14 21:43:10")],
                 [(0x9003, "2026:03:14 21:43:10")], (W, H))
    return png(scene(), exif, {"Comment": "DEMONSTRATION DATA - NOT REAL EVIDENCE"})


def photo_f() -> bytes:
    px = scene()
    # Copy-move: a 44x36 patch of forklift-and-wall texture pasted over the sign.
    sx, sy, dx, dy, pw, ph = 170, 70, 40, 2, 44, 36
    patch = [row[sx:sx + pw] for row in px[sy:sy + ph]]
    for j in range(ph):
        px[dy + j][dx:dx + pw] = patch[j]
    exif = _exif([(0x010F, "DemoCam"), (0x0110, "DC-1 Still"), (0x0132, "2026:03:15 09:12:44")],
                 [(0x9003, "2026:03:14 21:43:10")], (W, H))
    return png(px, exif, {"Comment": "DEMONSTRATION DATA - NOT REAL EVIDENCE",
                          "Software": "GIMP 2.10.36"}, trailing=b"DEMO-TRAILER-0001")


# --------------------------------------------------------------------------
# MP4 (container only)
# --------------------------------------------------------------------------
def _box(btype: str, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + btype.encode("latin-1") + payload


def _full(btype: str, payload: bytes, version: int = 0, flags: int = 0) -> bytes:
    return _box(btype, bytes([version]) + flags.to_bytes(3, "big") + payload)


MATRIX = struct.pack(">9I", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000)


def _trak(track_id: int, handler: str, timescale: int, duration: int, created: int,
          modified: int, stts: list[tuple[int, int]], movie_duration_ms: int) -> bytes:
    width, height = (640, 360) if handler == "vide" else (0, 0)
    tkhd = _full("tkhd", struct.pack(">IIIII", created, modified, track_id, 0, movie_duration_ms)
                 + b"\x00" * 8 + struct.pack(">hhhH", 0, 0, 0x100 if handler == "soun" else 0, 0)
                 + MATRIX + struct.pack(">II", width << 16, height << 16), flags=3)
    mdhd = _full("mdhd", struct.pack(">IIIIHH", created, modified, timescale, duration,
                                     0x55C4, 0))
    hdlr = _full("hdlr", struct.pack(">I", 0) + handler.encode("latin-1") + b"\x00" * 12
                 + b"DemoHandler\x00")
    stts_box = _full("stts", struct.pack(">I", len(stts))
                     + b"".join(struct.pack(">II", c, d) for c, d in stts))
    stbl = _box("stbl", _full("stsd", struct.pack(">I", 0)) + stts_box
                + _full("stsc", struct.pack(">I", 0)) + _full("stsz", struct.pack(">II", 0, 0))
                + _full("stco", struct.pack(">I", 0)))
    minf = _box("minf", stbl)
    return _box("trak", tkhd + _box("mdia", mdhd + hdlr + minf))


def mp4(created: int, modified: int, video_runs: list[tuple[int, int]], audio_ms: int,
        encoder: str) -> bytes:
    video_ms = sum(c * d for c, d in video_runs)
    ftyp = _box("ftyp", b"isom" + struct.pack(">I", 512) + b"isomiso2mp41")
    mvhd = _full("mvhd", struct.pack(">IIII", created, modified, 1000, video_ms)
                 + struct.pack(">IH", 0x10000, 0x100) + b"\x00" * 10 + MATRIX + b"\x00" * 24
                 + struct.pack(">I", 3))
    text = encoder.encode("utf-8")
    udta = _box("udta", _box("©too", struct.pack(">HH", len(text), 0x55C4) + text))
    moov = _box("moov", mvhd
                + _trak(1, "vide", 1000, video_ms, created, modified, video_runs, video_ms)
                + _trak(2, "soun", 8000, audio_ms * 8, created, modified,
                        [(audio_ms * 8 // 1024, 1024)], audio_ms)
                + udta)
    return ftyp + moov + _box("mdat", b"")


VIDEO_A_RUNS = [(425, 40)] + [(1, 48), (1, 32)] * 25 + [(575, 40), (1, 2000)]
VIDEO_A1_RUNS = [(500, 40)]


# --------------------------------------------------------------------------
# WAV
# --------------------------------------------------------------------------
def wav() -> bytes:
    rate = 8000
    rng = LCG(1234)
    samples: list[int] = []
    for i in range(rate * 8):
        if i >= rate * 5:                        # second room: louder floor + decaying step
            v = rng.between(-1500, 1500)
            k = i - rate * 5
            if k < 440:
                v += 11000 - 25 * k
        else:
            v = rng.between(-300, 300)
            if rate <= i < 4 * rate and (i // (rate // 2)) % 2 == 0:  # alarm: 0.5 s beeps
                v += BEEP[i % 8]
        if rate * 240 // 100 <= i < rate * 255 // 100:  # muted passage: exact zeros
            v = 0
        samples.append(max(-32768, min(32767, v)))
    data = struct.pack(f"<{len(samples)}h", *samples)
    info = b"INFO"
    for tag, text in (("ICRD", "2026-03-14T21:43:31"), ("ISFT", "DemoRecorder R1 1.0"),
                      ("ICMT", "DEMONSTRATION DATA - NOT REAL EVIDENCE")):
        raw = text.encode("latin-1") + b"\x00"
        info += tag.encode() + struct.pack("<I", len(raw)) + raw + (b"\x00" if len(raw) % 2 else b"")
    fmt = struct.pack("<HHIIHH", 1, 1, rate, rate * 2, 2, 16)
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"LIST"
            + struct.pack("<I", len(info)) + info + b"data" + struct.pack("<I", len(data)) + data)
    return b"RIFF" + struct.pack("<I", len(body)) + body


# --------------------------------------------------------------------------
# Case
# --------------------------------------------------------------------------
def _json(obj: dict) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def build() -> dict[str, bytes]:
    """Every demo file, keyed by its path relative to data/truth-forensics/."""
    files: dict[str, bytes] = {}
    files["demo/video-a.mp4"] = mp4(T_CAPTURE, T_CAPTURE, VIDEO_A_RUNS, 42000,
                                    "DemoCam DC-1 firmware 2.4")
    files["demo/video-a-trim.mp4"] = mp4(T_CAPTURE, T_EXPORT, VIDEO_A1_RUNS, 20000,
                                         "Lavf60.16.100")
    files["demo/photo-b.png"] = photo_b()
    files["demo/photo-b-copy.png"] = photo_b()
    files["demo/photo-f.png"] = photo_f()
    files["demo/audio-c.wav"] = wav()
    files["demo/document-d.txt"] = (
        "NORTHWIND DEMO DEPOT - DISPATCH LOG\n"
        "DEMONSTRATION DATA - NOT REAL EVIDENCE (fictional record)\n"
        "2026-03-14 21:43 Dock 2 door opened for loading\n"
        "2026-03-14 21:43 Forklift FL-3 moved Pallet 7 out of Dock 2\n"
        "2026-03-14 21:44 Dock 2 door closed\n").encode("utf-8")
    files["demo/sensor-e.json"] = _json({
        "record_type": "sensor-window", "sensor": "door sensor DS-2",
        "location": "Northwind Demo Depot, Dock 2", "start": "2026-03-14T21:43:22",
        "end": "2026-03-14T21:43:45", "demonstration": True})
    files["demo/clock-h.json"] = _json({
        "record_type": "clock-reference", "device": "cam-dock-02", "offset_seconds": 7,
        "reference": "depot time server (fictional)", "measured_at": "2026-03-15T08:00:00",
        "demonstration": True})
    files["demo/custody-k.json"] = _json({
        "record_type": "custody-receipt", "issued_by": "Northwind Demo Depot security desk "
        "(fictional)", "issued_at": "2026-03-15T08:05:00", "demonstration": True,
        "entries": [{"evidence_id": "EV-A", "sha256": sha256_bytes(files["demo/video-a.mp4"])},
                    {"evidence_id": "EV-B", "sha256": sha256_bytes(files["demo/photo-b.png"])}]})
    files["demo-case.json"] = _json(case_manifest())
    return files


def _item(eid, label, file, at, **extra) -> dict:
    return {"evidence_id": eid, "label": label, "file": file, "acquired_at": at,
            "acquired_by": "demo-intake", **extra}


def case_manifest() -> dict:
    at = "2026-03-16T14:00:00Z"
    return {
        "schema": vocab.CASE_SCHEMA,
        "case_id": "TF-DEMO-0001",
        "title": "Northwind Demo Depot, Dock 2 (fictional demonstration case)",
        "demonstration": True,
        "label": vocab.DEMO_LABEL,
        "analyst": "demo-analyst",
        "analysis_at": "2026-03-16T15:00:00Z",
        "tolerances": {"time_seconds": 120, "location_meters": 250, "clock_seconds": 5},
        "claim": CLAIM,
        "evidence": [
            _item("EV-A", "Video A", "demo/video-a.mp4", at, upstream_source="cam-dock-02",
                  declared_mime="video/mp4", observations=[
                      {"dimension": "location", "value": "Northwind Demo Depot, Dock 2",
                       "basis": "painted dock number visible in frame"},
                      {"dimension": "identity", "value": "Forklift FL-3", "entity": "object",
                       "basis": "fleet number visible on the vehicle"},
                      {"dimension": "event", "value": "Forklift moves Pallet 7 out of Dock 2",
                       "basis": "description of 00:19-00:42"},
                      {"dimension": "device", "value": "cam-dock-02",
                       "basis": "camera id in the frame overlay"}]),
            _item("EV-A1", "Video A (trimmed export)", "demo/video-a-trim.mp4", at,
                  object_kind="DERIVATIVE", parent_id="EV-A",
                  transformation="trim 00:10-00:30 and re-encode (declared by submitter)"),
            _item("EV-B", "Photo B", "demo/photo-b.png", at, upstream_source="still-camera-dc1",
                  declared_mime="image/png", observations=[
                      {"dimension": "identity", "value": "Forklift FL-3", "entity": "object",
                       "basis": "fleet number visible on the vehicle"},
                      {"dimension": "event", "value": "Pallet 7 on the forklift forks",
                       "basis": "visible in frame"}]),
            _item("EV-B2", "Photo B (forwarded copy)", "demo/photo-b-copy.png", at,
                  declared_mime="image/png"),
            _item("EV-F", "Photo F (social repost)", "demo/photo-f.png", at,
                  upstream_source="social-repost-unknown", declared_mime="image/jpeg",
                  observations=[
                      {"dimension": "location", "value": "Northwind Demo Depot, Dock 4",
                       "basis": "dock sign appears to read 4"},
                      {"dimension": "identity", "value": "Forklift FL-3", "entity": "object",
                       "basis": "fleet number visible on the vehicle"}]),
            _item("EV-C", "Audio C", "demo/audio-c.wav", at, upstream_source="recorder-r1",
                  observations=[{"dimension": "event", "value": "reversing alarm audible",
                                 "basis": "listening review"}]),
            _item("EV-D", "Document D (dispatch log)", "demo/document-d.txt", at,
                  upstream_source="dispatch-desk", observations=[
                      {"dimension": "time", "value": "2026-03-14T21:43",
                       "basis": "dispatch log line 4, transcribed"},
                      {"dimension": "location", "value": "Northwind Demo Depot, Dock 2",
                       "basis": "dispatch log header and line 4"},
                      {"dimension": "identity", "value": "Forklift FL-3", "entity": "object",
                       "basis": "dispatch log line 4"},
                      {"dimension": "event",
                       "value": "Forklift FL-3 moved Pallet 7 out of Dock 2",
                       "basis": "dispatch log line 4"}]),
            _item("EV-E", "Timeline E (door-sensor log)", "demo/sensor-e.json", at,
                  upstream_source="door-sensor-ds2"),
            _item("EV-H", "Clock reference H", "demo/clock-h.json", at,
                  upstream_source="depot-time-server"),
            _item("EV-K", "Custody receipt K", "demo/custody-k.json", at,
                  upstream_source="security-desk"),
        ],
        "channels": [
            {"kind": "PRIMARY_MEDIA", "evidence_id": "EV-A", "label": "Video A"},
            {"kind": "INDEPENDENT_SENSOR", "evidence_id": "EV-E", "label": "Door sensor DS-2"},
            {"kind": "TIME_SOURCE", "evidence_id": "EV-H", "label": "Depot time server"},
            {"kind": "PROVENANCE_RECORD", "evidence_id": "EV-K", "label": "Custody receipt K"},
        ],
        "reviews": [],
        "suggested_reviews": [
            {"action": "REJECT", "target": "EV-F", "reviewer": "reviewer-1",
             "at": "2026-03-16T16:00:00Z",
             "note": "Cloned region over the dock sign, editor tag and time mismatch. The Dock 4 "
                     "reading comes from an altered area; exclude this item."},
            {"action": "ACCEPT", "target": "CLAIM", "reviewer": "reviewer-2",
             "at": "2026-03-16T16:20:00Z",
             "note": "Second reviewer: assessment accepted with EV-F excluded. Frame gap at "
                     "00:42 remains open and is outside the claimed window."},
        ],
    }


def load_files(case: dict, base: Path) -> dict[str, bytes]:
    """Read each item's file under `base`, refusing traversal and symlinks."""
    from .intake import safe_open_path

    out = {}
    for item in case["evidence"]:
        path = safe_open_path(base / item["file"], root=base)
        out[item["evidence_id"]] = path.read_bytes()
    return out


def write(base: Path = CASE_FILE.parent) -> list[str]:
    changed = []
    for rel, data in build().items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
            changed.append(rel)
    return changed


def check(base: Path = CASE_FILE.parent) -> list[str]:
    return [rel for rel, data in build().items()
            if not (base / rel).is_file() or (base / rel).read_bytes() != data]
