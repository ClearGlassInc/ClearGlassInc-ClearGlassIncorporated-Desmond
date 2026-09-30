# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Audio analysis for RIFF/WAVE (PCM 8/16/24/32-bit and 32-bit float).

Samples are brought to a common 16-bit scale and every test below uses
integer arithmetic, so the browser engine reproduces the same findings.

    digital silence     exact-zero runs of 10 ms or more inside the recording
    discontinuity       a sample step of at least 1/4 full scale that is also
                        more than 8x the mean step of the 32 samples either side
    noise-floor shift   the quietest 100 ms of adjacent seconds differ by 4x
                        (about 12 dB) while both stay at or below the 75th
                        percentile of all 100 ms windows (the quiet regime)
    clipping            samples at full scale
    channel relation    identical, polarity-inverted or independent

Other codecs (MP3, AAC, FLAC, Ogg) are recognised at intake and hashed; this
reference engine has no decoder for them. The browser console decodes them
with the Web Audio API and applies the same tests.
"""
from __future__ import annotations

import math
import re
import struct

from . import vocab
from .indicators import (
    Indicator,
    parse_error_indicator,
    parse_message,
    quote,
    software_indicators,
)

ANALYZER = "audio@" + vocab.ENGINE_VERSION
FULL_SCALE = 32768
MAX_ANALYSIS_FRAMES = 48000 * 600
STEP_WINDOW = 32
MAX_EVENTS = 20

NOT_PERFORMED = [
    "Speaker-consistency analysis (adapter boundary; not implemented)",
    "Synthetic-speech / voice-clone classifier (adapter boundary; no model bundled)",
    "Electrical network frequency (ENF) analysis (not implemented)",
]


class ParseError(ValueError):
    pass


def parse_wav(data: bytes) -> dict:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ParseError("not a RIFF/WAVE file")
    (riff_size,) = struct.unpack("<I", data[4:8])
    info: dict = {"riff_size": riff_size, "file_size": len(data), "fmt": None,
                  "data_offset": None, "data_size": 0, "chunks": [], "info_tags": {}}
    pos = 12
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4].decode("latin-1")
        (size,) = struct.unpack("<I", data[pos + 4:pos + 8])
        body_start = pos + 8
        info["chunks"].append({"id": cid, "size": size})
        if len(info["chunks"]) > 10_000:
            raise ParseError("implausible chunk count")
        if cid == "data":
            info["data_offset"] = body_start
            info["data_size"] = min(size, len(data) - body_start)
            info["data_truncated"] = size > len(data) - body_start
        elif body_start + size > len(data):
            raise ParseError(f"chunk {quote(cid)} runs past the end of the file")
        elif cid == "fmt ":
            if size < 16:
                raise ParseError("fmt chunk too short")
            fmt_tag, ch, rate, _, align, bits = struct.unpack("<HHIIHH", data[body_start:body_start + 16])
            if fmt_tag == 0xFFFE and size >= 40:
                fmt_tag = struct.unpack("<H", data[body_start + 24:body_start + 26])[0]
            info["fmt"] = {"format": fmt_tag, "channels": ch, "sample_rate": rate,
                           "block_align": align, "bits": bits}
        elif cid == "LIST" and data[body_start:body_start + 4] == b"INFO":
            p, end = body_start + 4, body_start + size
            while p + 8 <= end:
                tag = data[p:p + 4].decode("latin-1")
                (ln,) = struct.unpack("<I", data[p + 4:p + 8])
                if p + 8 + ln > end:
                    break
                info["info_tags"][tag] = data[p + 8:p + 8 + ln].split(b"\x00", 1)[0].decode(
                    "latin-1")[:400]
                p += 8 + ln + (ln & 1)
        pos = body_start + size + (size & 1)
    if info["fmt"] is None or info["data_offset"] is None:
        raise ParseError("fmt or data chunk missing")
    return info


def decode_samples(data: bytes, info: dict) -> tuple[list[list[int]], str]:
    """Per-channel samples on a 16-bit scale. Returns (channels, note)."""
    fmt = info["fmt"]
    ch, bits, tag = fmt["channels"], fmt["bits"], fmt["format"]
    if ch < 1 or ch > 8:
        raise ParseError(f"unsupported channel count {ch}")
    width = bits // 8
    if tag == 1 and bits in (8, 16, 24, 32):
        pass
    elif tag == 3 and bits == 32:
        pass
    else:
        raise ParseError(f"unsupported sample format (tag {tag}, {bits}-bit)")
    frame = width * ch
    raw = data[info["data_offset"]:info["data_offset"] + info["data_size"]]
    frames = len(raw) // frame
    note = ""
    if frames > MAX_ANALYSIS_FRAMES:
        frames = MAX_ANALYSIS_FRAMES
        note = "analysis limited to the first 10 minutes"
    raw = raw[:frames * frame]
    count = frames * ch
    if tag == 3:
        vals = struct.unpack(f"<{count}f", raw)
        conv = []
        for v in vals:
            # NaN -> silence; out-of-range and infinite samples clip to full scale.
            v = 0.0 if v != v else 1.0 if v > 1.0 else -1.0 if v < -1.0 else v
            conv.append(math.floor(v * 32767 + 0.5))
    elif bits == 8:
        conv = [(b - 128) << 8 for b in raw]
    elif bits == 16:
        conv = list(struct.unpack(f"<{count}h", raw))
    elif bits == 24:
        conv = []
        for i in range(0, len(raw), 3):
            v = raw[i] | (raw[i + 1] << 8) | (raw[i + 2] << 16)
            if v & 0x800000:
                v -= 0x1000000
            conv.append(v >> 8)
    else:
        conv = [v >> 16 for v in struct.unpack(f"<{count}i", raw)]
    return [conv[c::ch] for c in range(ch)], note


def analyze_pcm(channels: list[list[int]], rate: int) -> dict:
    """Integer-only tests on decoded PCM. Shared rules with the browser engine."""
    n = len(channels[0]) if channels else 0
    nch = len(channels)
    out: dict = {"frames": n, "duration_ms": n * 1000 // rate if rate else 0,
                 "digital_silence": [], "discontinuities": [], "noise_floor_shifts": [],
                 "clipped_samples": 0, "peak": 0, "channel_relation": "mono"}
    if n == 0 or rate <= 0:
        return out
    mix = channels[0] if nch == 1 else [
        sum(c[i] for c in channels) // nch for i in range(n)]
    peak = 0
    clipped = 0
    for c in channels:
        for v in c:
            a = -v if v < 0 else v
            if a > peak:
                peak = a
            if a >= 32767:
                clipped += 1
    out["peak"] = peak
    out["clipped_samples"] = clipped
    if nch == 2:
        left, right = channels
        if left == right:
            out["channel_relation"] = "identical"
        elif all(a == -b for a, b in zip(left, right)):
            out["channel_relation"] = "inverted"
        else:
            out["channel_relation"] = "independent"
    elif nch > 2:
        out["channel_relation"] = "multichannel"

    # Digital silence: every channel exactly zero, inside the recording.
    min_run = max(1, rate * 10 // 1000)
    silent_runs: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if all(c[i] == 0 for c in channels):
            j = i
            while j < n and all(c[j] == 0 for c in channels):
                j += 1
            if j - i >= min_run and i > 0 and j < n:
                silent_runs.append((i, j))
            i = j
        else:
            i += 1
    out["digital_silence"] = [[a * 1000 // rate, b * 1000 // rate] for a, b in silent_runs[:MAX_EVENTS]]

    # Discontinuities: a large step that towers over its neighbourhood.
    steps = [0] * n
    for k in range(1, n):
        d = mix[k] - mix[k - 1]
        steps[k] = -d if d < 0 else d
    prefix = [0] * (n + 1)
    for k in range(n):
        prefix[k + 1] = prefix[k] + steps[k]
    edges = set()
    for a, b in silent_runs:
        edges.update((a, a + 1, b, b + 1))
    hits: list[int] = []
    threshold = FULL_SCALE // 4
    for k in range(1, n):
        s = steps[k]
        if s < threshold or k in edges:
            continue
        lo, hi = max(1, k - STEP_WINDOW), min(n, k + STEP_WINDOW + 1)
        neighbours = (prefix[hi] - prefix[lo]) - s
        count = (hi - lo) - 1
        if count > 0 and s * count > 8 * neighbours:
            hits.append(k)
    grouped: list[int] = []
    gap = max(1, rate // 100)
    for k in hits:
        if not grouped or k - grouped[-1] > gap:
            grouped.append(k)
    out["discontinuities"] = [k * 1000 // rate for k in grouped[:MAX_EVENTS]]

    # Noise-floor shift between adjacent seconds.
    win = max(1, rate // 10)
    window_rms = []
    for start in range(0, n - win + 1, win):
        acc = 0
        for v in mix[start:start + win]:
            acc += v * v
        window_rms.append(math.isqrt(acc // win))
    if len(window_rms) >= 20:
        ordered = sorted(window_rms)
        quiet_ceiling = ordered[3 * len(ordered) // 4]
        floors = [min(window_rms[s:s + 10]) for s in range(0, len(window_rms) - 9, 10)]
        for k in range(len(floors) - 1):
            a, b = floors[k], floors[k + 1]
            if a == 0 or b == 0:
                continue
            hi_, lo_ = max(a, b), min(a, b)
            if hi_ >= 4 * lo_ and hi_ <= quiet_ceiling:
                out["noise_floor_shifts"].append({"at_ms": (k + 1) * 1000, "from": a, "to": b})
    return out


def _indicators(metrics: dict) -> list[Indicator]:
    out: list[Indicator] = []
    if metrics["digital_silence"]:
        spans = ", ".join(f"{a}-{b} ms" for a, b in metrics["digital_silence"])
        out.append(Indicator(
            code="AUDIO.DIGITAL_SILENCE",
            category="AUDIO",
            title="Exact digital silence inside the recording",
            evidence=f"all channels exactly zero for: {spans}",
            method="Run-length scan for exact-zero samples lasting 10 ms or more, "
                   "excluding the start and end of the file.",
            confidence="MODERATE",
            limitation=(
                "A live microphone almost never outputs exact zeros, but gating, muting and "
                "some codecs do. Shows where to listen, not what was removed."
            ),
            alternatives=("Noise gate or hardware mute", "Codec silence suppression",
                          "Deliberate muting of a passage"),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
            location=spans,
        ))
    if metrics["discontinuities"]:
        spots = ", ".join(f"{t} ms" for t in metrics["discontinuities"])
        out.append(Indicator(
            code="AUDIO.DISCONTINUITY",
            category="AUDIO",
            title="Abrupt waveform discontinuity (possible splice point)",
            evidence=f"step of at least 1/4 full scale, over 8x the local mean step, at: {spots}",
            method="Sample-to-sample step compared with the mean step of 32 samples either side.",
            confidence="LOW",
            limitation=(
                "Sharp transients such as clicks, knocks and plosives produce the same step. "
                "Needs listening and spectral review at each point."
            ),
            alternatives=("Percussive transient", "Microphone bump or cable click",
                          "Recovery from clipping", "Dropout during capture"),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
            location=spots,
        ))
    if metrics["noise_floor_shifts"]:
        spots = ", ".join(f"{s['at_ms']} ms" for s in metrics["noise_floor_shifts"])
        out.append(Indicator(
            code="AUDIO.NOISE_FLOOR_SHIFT",
            category="AUDIO",
            title="Background-noise level changes abruptly",
            evidence="quietest-100-ms level changes 4x or more between adjacent seconds at: "
                     + spots,
            method="Per-second minimum of 100 ms RMS windows, compared across adjacent seconds.",
            confidence="LOW",
            limitation=(
                "Room-tone changes can come from real events. The test cannot tell a join "
                "between two recordings from a change in the room."
            ),
            alternatives=("HVAC, traffic or machinery switching on or off",
                          "Automatic gain control", "Speaker moving relative to the microphone"),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
            location=spots,
        ))
    total = metrics["frames"] * max(1, metrics.get("channels", 1))
    if total and metrics["clipped_samples"] * 1000 > total:
        out.append(Indicator(
            code="AUDIO.CLIPPING",
            category="AUDIO",
            title="Clipping above 0.1% of samples",
            evidence=f"{metrics['clipped_samples']} of {total} samples at full scale",
            method="Count of samples at digital full scale.",
            confidence="HIGH",
            limitation="A recording-quality issue, not a manipulation signal. It degrades the "
                       "discontinuity test.",
            alternatives=("Input gain set too high",),
            state=vocab.NORMAL,
            analyzer=ANALYZER,
        ))
    return out


def analyze_audio(data: bytes, mime: str) -> dict:
    result: dict = {"analyzer": ANALYZER, "metadata": {}, "indicators": [], "observations": [],
                    "not_performed": list(NOT_PERFORMED), "metrics": None}
    if mime != "audio/wav":
        result["not_performed"].append(
            f"Sample analysis of {mime} (no decoder in the reference engine; the browser "
            "console decodes it with the Web Audio API)")
        return result
    try:
        info = parse_wav(data)
        channels, note = decode_samples(data, info)
    except (ParseError, struct.error) as exc:
        result["indicators"].append(parse_error_indicator(parse_message(exc), ANALYZER))
        return result
    fmt = info["fmt"]
    metrics = analyze_pcm(channels, fmt["sample_rate"])
    metrics["channels"] = fmt["channels"]
    result["metrics"] = metrics
    result["metadata"] = {
        "format": "wav", "codec": "float32" if fmt["format"] == 3 else f"pcm{fmt['bits']}",
        "sample_rate": fmt["sample_rate"], "channels": fmt["channels"], "bits": fmt["bits"],
        "duration_ms": metrics["duration_ms"], "info_tags": info["info_tags"],
        "chunks": [c["id"] for c in info["chunks"]], "note": note,
    }
    inds = result["indicators"]
    if info["riff_size"] + 8 != info["file_size"] or info.get("data_truncated"):
        inds.append(Indicator(
            code="CONTAINER.SIZE_MISMATCH",
            category="CONTAINER",
            title="RIFF size fields disagree with the file length",
            evidence=f"RIFF declares {info['riff_size'] + 8} bytes; file is {info['file_size']}"
                     + ("; data chunk is truncated" if info.get("data_truncated") else ""),
            method="RIFF header and chunk-size consistency check.",
            confidence="HIGH",
            limitation="Shows the file was truncated, extended or rewritten without fixing "
                       "headers; not what changed.",
            alternatives=("Interrupted recording or transfer", "Tool that appends data"),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
        ))
    inds.extend(software_indicators("RIFF INFO ISFT", info["info_tags"].get("ISFT", ""), ANALYZER))
    inds.extend(_indicators(metrics))
    created = info["info_tags"].get("ICRD", "")
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?))?", created.strip(),
                     re.ASCII)
    if m:
        value = m.group(1) + ("T" + m.group(2) if m.group(2) else "")
        result["observations"].append({"dimension": "time", "value": value,
                                       "basis": "RIFF INFO ICRD (unsigned metadata)"})
    return result
