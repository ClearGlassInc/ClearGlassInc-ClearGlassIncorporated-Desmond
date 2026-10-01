# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Video container analysis for ISO BMFF (MP4 / MOV / M4V).

Reads the box tree without decoding a single frame:

    ftyp        brands
    mvhd        creation / modification time, timescale, duration
    trak        tkhd, mdhd, hdlr, stts (frame intervals), stss, ctts, elst
    udta        encoder (©too / ©swr), date (©day), location (©xyz)
    moof        fragmented files: timing lives in trun, which is not read

The frame-interval table feeds `timeline.build`, which is where frame gaps,
duplicate timestamps and irregular intervals are found. Pixel-level tests
(optical flow, face or object persistence, lighting) are not implemented;
the browser console adds a sampled-frame fingerprint pass for files the
browser can play.
"""
from __future__ import annotations

import re
import struct
from datetime import datetime, timezone

from . import timeline, vocab
from .indicators import (
    Indicator,
    parse_error_indicator,
    parse_message,
    quote,
    software_indicators,
)

ANALYZER = "video@" + vocab.ENGINE_VERSION
EPOCH_1904 = 2082844800
MAX_BOXES = 200_000
MAX_DEPTH = 16
MAX_STTS_ENTRIES = 2_000_000

CONTAINERS = {"moov", "trak", "mdia", "minf", "stbl", "edts", "udta", "dinf", "ilst", "moof",
              "traf", "mvex"}
TEXT_TAGS = {"©too": "encoder", "©swr": "encoder", "©day": "date",
             "©xyz": "location"}

NOT_PERFORMED = [
    "Optical-flow and motion-consistency analysis (not implemented)",
    "Face / identity and object-persistence tracking (not implemented)",
    "Lighting-consistency analysis (not implemented)",
    "Frame decoding in the reference engine (container timing only)",
]


class ParseError(ValueError):
    pass


def _mac_time(value: int) -> str:
    if value == 0:
        return ""
    unix = value - EPOCH_1904
    try:
        return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    except (OverflowError, OSError, ValueError):
        return ""


def walk(data: bytes, start: int, end: int, depth: int, counter: list[int]) -> list[dict]:
    boxes = []
    pos = start
    while pos + 8 <= end:
        counter[0] += 1
        if counter[0] > MAX_BOXES:
            raise ParseError("implausible box count")
        size, raw_type = struct.unpack(">I4s", data[pos:pos + 8])
        btype = raw_type.decode("latin-1")
        header = 8
        if size == 1:
            if pos + 16 > end:
                raise ParseError("64-bit box size truncated")
            (size,) = struct.unpack(">Q", data[pos + 8:pos + 16])
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            raise ParseError(f"box {quote(btype)} at offset {pos} overruns its parent")
        box = {"type": btype, "offset": pos, "size": size, "header": header, "children": []}
        body = pos + header
        if depth < MAX_DEPTH:
            if btype in CONTAINERS:
                box["children"] = walk(data, body, pos + size, depth + 1, counter)
            elif btype == "meta" and pos + size - body >= 4:
                box["children"] = walk(data, body + 4, pos + size, depth + 1, counter)
            elif btype in TEXT_TAGS and _has_data_child(data, body, pos + size):
                box["children"] = walk(data, body, pos + size, depth + 1, counter)
        boxes.append(box)
        pos += size
    return boxes


def _has_data_child(data: bytes, body: int, end: int) -> bool:
    return end - body >= 16 and data[body + 4:body + 8] == b"data"


def _find(boxes: list[dict], btype: str) -> dict | None:
    for b in boxes:
        if b["type"] == btype:
            return b
    return None


def _all(boxes: list[dict], btype: str) -> list[dict]:
    out = []
    for b in boxes:
        if b["type"] == btype:
            out.append(b)
        out.extend(_all(b["children"], btype))
    return out


def _body(data: bytes, box: dict) -> bytes:
    return data[box["offset"] + box["header"]:box["offset"] + box["size"]]


def _full_header(body: bytes) -> int:
    if len(body) < 4:
        raise ParseError("full box too short")
    return body[0]


def _parse_mvhd(body: bytes) -> dict:
    v = _full_header(body)
    if v == 1:
        c, m, ts, dur = struct.unpack(">QQIQ", body[4:32])
    else:
        c, m, ts, dur = struct.unpack(">IIII", body[4:20])
    return {"creation": c, "modification": m, "timescale": ts, "duration": dur}


def _parse_mdhd(body: bytes) -> dict:
    v = _full_header(body)
    if v == 1:
        c, m, ts, dur = struct.unpack(">QQIQ", body[4:32])
    else:
        c, m, ts, dur = struct.unpack(">IIII", body[4:20])
    return {"timescale": ts, "duration": dur}


def _parse_tkhd(body: bytes) -> dict:
    v = _full_header(body)
    if v == 1:
        track_id = struct.unpack(">I", body[20:24])[0]
        tail = 4 + 8 + 8 + 4 + 4 + 8 + 8 + 2 + 2 + 2 + 2 + 36
    else:
        track_id = struct.unpack(">I", body[12:16])[0]
        tail = 4 + 4 + 4 + 4 + 4 + 4 + 8 + 2 + 2 + 2 + 2 + 36
    w = h = 0
    if len(body) >= tail + 8:
        w, h = struct.unpack(">II", body[tail:tail + 8])
    return {"track_id": track_id, "width": w >> 16, "height": h >> 16}


def _parse_stts(body: bytes) -> list[tuple[int, int]]:
    _full_header(body)
    (count,) = struct.unpack(">I", body[4:8])
    if count > MAX_STTS_ENTRIES or 8 + 8 * count > len(body):
        raise ParseError("stts entry table out of range")
    vals = struct.unpack(f">{2 * count}I", body[8:8 + 8 * count])
    return [(vals[2 * i], vals[2 * i + 1]) for i in range(count)]


def _parse_elst(body: bytes) -> list[dict]:
    v = _full_header(body)
    (count,) = struct.unpack(">I", body[4:8])
    entries = []
    size = 20 if v == 1 else 12
    if count > 10_000 or 8 + size * count > len(body):
        raise ParseError("elst entry table out of range")
    for i in range(count):
        p = 8 + size * i
        if v == 1:
            seg, media = struct.unpack(">Qq", body[p:p + 16])
        else:
            seg, media = struct.unpack(">Ii", body[p:p + 8])
        entries.append({"segment_duration": seg, "media_time": media})
    return entries


def _tag_text(data: bytes, box: dict) -> str:
    body = _body(data, box)
    if box["children"]:
        d = _find(box["children"], "data")
        if d:
            return _body(data, d)[8:].decode("utf-8", "replace")[:400]
    if len(body) >= 4:
        (ln,) = struct.unpack(">H", body[:2])
        return body[4:4 + ln].decode("utf-8", "replace")[:400]
    return ""


def iso6709(value: str) -> str:
    m = re.match(r"([+-]\d{1,3}(?:\.\d+)?)([+-]\d{1,3}(?:\.\d+)?)", value.strip(), re.ASCII)
    if not m:
        return ""

    def five(s: str) -> str:
        sign = "-" if s.startswith("-") else ""
        whole, _, frac = s.lstrip("+-").partition(".")
        frac = (frac + "00000")[:5]
        return f"{sign}{int(whole)}.{frac}"

    return f"{five(m.group(1))},{five(m.group(2))}"


def parse_bmff(data: bytes) -> dict:
    info: dict = {"brands": [], "movie": None, "tracks": [], "tags": {}, "fragmented": False,
                  "top_level": [], "parse_error": ""}
    try:
        boxes = walk(data, 0, len(data), 0, [0])
    except (ParseError, struct.error) as exc:
        info["parse_error"] = parse_message(exc)
        return info
    info["top_level"] = [b["type"] for b in boxes]
    try:
        ftyp = _find(boxes, "ftyp")
        if ftyp:
            body = _body(data, ftyp)
            info["brands"] = [body[0:4].decode("latin-1")] + [
                body[i:i + 4].decode("latin-1") for i in range(8, len(body) - 3, 4)]
        moov = _find(boxes, "moov")
        info["fragmented"] = any(b["type"] == "moof" for b in boxes)
        if moov is None:
            raise ParseError("no moov box")
        mvhd = _find(moov["children"], "mvhd")
        if mvhd:
            info["movie"] = _parse_mvhd(_body(data, mvhd))
        for trak in (b for b in moov["children"] if b["type"] == "trak"):
            track: dict = {"handler": "", "timescale": 0, "duration": 0, "stts": [],
                           "sync_samples": None, "ctts": False, "edits": [], "width": 0,
                           "height": 0, "track_id": 0}
            tkhd = _find(trak["children"], "tkhd")
            if tkhd:
                track.update(_parse_tkhd(_body(data, tkhd)))
            for box in _all(trak["children"], "mdhd"):
                track.update(_parse_mdhd(_body(data, box)))
            for box in _all(trak["children"], "hdlr"):
                track["handler"] = _body(data, box)[8:12].decode("latin-1")
            for box in _all(trak["children"], "stts"):
                track["stts"] = _parse_stts(_body(data, box))
            for box in _all(trak["children"], "stss"):
                track["sync_samples"] = struct.unpack(">I", _body(data, box)[4:8])[0]
            track["ctts"] = bool(_all(trak["children"], "ctts"))
            for box in _all(trak["children"], "elst"):
                track["edits"] = _parse_elst(_body(data, box))
            info["tracks"].append(track)
        for tag, key in TEXT_TAGS.items():
            for box in _all(boxes, tag):
                info["tags"].setdefault(key, _tag_text(data, box))
    except (ParseError, struct.error) as exc:
        info["parse_error"] = parse_message(exc)
    return info


def analyze_video(data: bytes, mime: str, supported_ms: list[tuple[int, int]] | None = None) -> dict:
    result: dict = {"analyzer": ANALYZER, "metadata": {}, "indicators": [], "observations": [],
                    "not_performed": list(NOT_PERFORMED), "timeline": None}
    if mime not in ("video/mp4", "video/quicktime", "audio/mp4"):
        result["not_performed"].append(f"Container analysis of {mime} (not implemented)")
        return result
    info = parse_bmff(data)
    inds = result["indicators"]
    if info["parse_error"]:
        inds.append(parse_error_indicator(info["parse_error"], ANALYZER))
    movie = info["movie"] or {}
    created = _mac_time(movie.get("creation", 0))
    modified = _mac_time(movie.get("modification", 0))
    duration_ms = (movie.get("duration", 0) * 1000 // movie["timescale"]
                   if movie.get("timescale") else 0)
    video = next((t for t in info["tracks"] if t["handler"] == "vide"), None)
    audio = next((t for t in info["tracks"] if t["handler"] == "soun"), None)

    def track_ms(t: dict | None) -> int | None:
        if not t or not t["timescale"]:
            return None
        return t["duration"] * 1000 // t["timescale"]

    result["metadata"] = {
        "format": "iso-bmff",
        "brands": info["brands"],
        "created": created,
        "modified": modified,
        "duration_ms": duration_ms,
        "tracks": [{"handler": t["handler"], "timescale": t["timescale"],
                    "duration_ms": track_ms(t), "width": t["width"], "height": t["height"],
                    "edits": len(t["edits"]), "sync_samples": t["sync_samples"]}
                   for t in info["tracks"]],
        "tags": info["tags"],
        "fragmented": info["fragmented"],
    }
    if video and video["stts"]:
        tl = timeline.build(video["stts"], video["timescale"], supported_ms)
        result["timeline"] = tl
        result["frame_runs"] = [[c, d] for c, d in video["stts"]]
        inds.extend(_timeline_indicators(tl))
    elif video is None and not info["parse_error"]:
        result["not_performed"].append("Frame-timing analysis (no video track)")
    v_ms, a_ms = track_ms(video), track_ms(audio)
    if v_ms is not None and a_ms is not None and abs(v_ms - a_ms) > 200:
        diff = abs(v_ms - a_ms)
        inds.append(Indicator(
            code="TEMPORAL.TRACK_DURATION_MISMATCH",
            category="TEMPORAL",
            title="Audio and video tracks differ in length",
            evidence=f"video track {v_ms} ms; audio track {a_ms} ms (difference {diff} ms)",
            method="Comparison of media-header durations for the video and sound tracks.",
            confidence="MODERATE" if diff > 1000 else "LOW",
            limitation=(
                "Edit lists can realign tracks at playback, and some devices start audio "
                "early. Shows a structural difference, not a sync error in what is heard."
            ),
            alternatives=("Recorder started one track before the other",
                          "Trim applied to one track only", "Audio replaced or dubbed"),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
        ))
    if video and (len(video["edits"]) > 1 or any(e["media_time"] == -1 for e in video["edits"])):
        inds.append(Indicator(
            code="TEMPORAL.EDIT_LIST",
            category="TEMPORAL",
            title="Video track has a non-trivial edit list",
            evidence=f"{len(video['edits'])} edit-list entries; empty edits: "
                     f"{sum(1 for e in video['edits'] if e['media_time'] == -1)}",
            method="Parse of the video track's elst box.",
            confidence="LOW",
            limitation="Edit lists change what plays without changing stored frames. Their "
                       "purpose is not recorded.",
            alternatives=("Encoder start offset", "Non-destructive trim in an editor"),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
        ))
    c, m = movie.get("creation", 0), movie.get("modification", 0)
    if info["movie"] and c == 0:
        inds.append(Indicator(
            code="PROVENANCE.NO_CREATION_TIME",
            category="PROVENANCE",
            title="Container creation time is unset",
            evidence="mvhd creation_time = 0",
            method="Parse of the movie header.",
            confidence="HIGH",
            limitation="Many export tools zero this field. It is a provenance gap only.",
            alternatives=("Export or remux tool default",),
            state=vocab.PROVENANCE_GAP,
            analyzer=ANALYZER,
        ))
    elif c and m and m - c > 60:
        inds.append(Indicator(
            code="METADATA.MODIFIED_AFTER_CREATION",
            category="METADATA",
            title="Container modified after it was created",
            evidence=f"mvhd creation {created}; modification {modified}",
            method="Comparison of movie-header creation and modification times.",
            confidence="LOW",
            limitation="Both fields are unsigned and rewritable. Remuxing or trimming updates "
                       "the modification time without touching content.",
            alternatives=("Trim, remux or export", "Metadata edit"),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
        ))
    if info["tags"].get("encoder"):
        inds.extend(software_indicators("encoder tag", info["tags"]["encoder"], ANALYZER))
    if info["fragmented"]:
        inds.append(Indicator(
            code="CONTAINER.FRAGMENTED",
            category="CONTAINER",
            title="Fragmented MP4: frame timing not fully analysed",
            evidence="moof boxes present",
            method="Top-level box inventory.",
            confidence="HIGH",
            limitation="Per-fragment timing (trun) is not read, so the timeline is incomplete.",
            alternatives=("Streaming or live-recording format",),
            state=vocab.INCONCLUSIVE,
            analyzer=ANALYZER,
        ))
    if created:
        result["observations"].append({
            "dimension": "time", "value": created,
            "basis": "MP4 mvhd creation_time (unsigned metadata; UTC by specification, "
                     "often local time in practice)"})
        if duration_ms:
            end = _mac_time(movie["creation"] + movie["duration"] // movie["timescale"])
            result["observations"].append({
                "dimension": "time_window", "value": f"{created}/{end}",
                "basis": "mvhd creation_time plus movie duration"})
    loc = iso6709(info["tags"].get("location", ""))
    if loc:
        result["observations"].append({"dimension": "location", "value": loc,
                                       "basis": "MP4 ©xyz tag (unsigned metadata)"})
    return result


def _timeline_indicators(tl: dict) -> list[Indicator]:
    out: list[Indicator] = []
    anomalies = [s for s in tl["segments"] if s["state"] == vocab.ANOMALY_DETECTED]
    irregular = [s for s in tl["segments"] if s["state"] == vocab.REVIEW_REQUIRED]
    fps = f"{tl['fps_x100'] // 100}.{tl['fps_x100'] % 100:02d}"
    if anomalies:
        where = "; ".join(f"{timeline.fmt_ms(s['start_ms'])}-{timeline.fmt_ms(s['end_ms'])} "
                          f"{s['reason']}" for s in anomalies[:10])
        out.append(Indicator(
            code="TEMPORAL.FRAME_TIMING_ANOMALY",
            category="TEMPORAL",
            title="Frame-timing discontinuity",
            evidence=f"nominal {fps} fps; {where}",
            method="Frame-interval table compared with the nominal interval "
                   "(gap >= 1.5x, zero or negative interval).",
            confidence="MODERATE",
            limitation=(
                "Timing tables are rewritten on every remux. A gap estimates missing frames; it "
                "cannot distinguish encoder drops from deletion."
            ),
            alternatives=("Encoder or storage frame drops under load",
                          "Recording paused and resumed", "Frames removed in editing"),
            state=vocab.ANOMALY_DETECTED,
            analyzer=ANALYZER,
            location=where,
        ))
    if irregular:
        where = "; ".join(f"{timeline.fmt_ms(s['start_ms'])}-{timeline.fmt_ms(s['end_ms'])}"
                          for s in irregular[:10])
        out.append(Indicator(
            code="TEMPORAL.IRREGULAR_INTERVALS",
            category="TEMPORAL",
            title="Irregular frame intervals",
            evidence=f"nominal {fps} fps; intervals more than 10% off nominal at {where}",
            method="Frame-interval table compared with the nominal interval.",
            confidence="LOW",
            limitation="Variable-frame-rate capture is normal on phones; this marks where to look.",
            alternatives=("Variable-frame-rate capture", "Frame-rate conversion"),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
            location=where,
        ))
    return out
