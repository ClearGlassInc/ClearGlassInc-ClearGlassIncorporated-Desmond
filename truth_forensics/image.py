# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Image analysis: container structure, EXIF, quantization, copy-move.

What runs here, and on what:

* JPEG  -- marker walk, EXIF (IFD0, Exif IFD, GPS IFD), XMP CreatorTool,
           quantization tables with an IJG quality estimate, C2PA manifest
           *presence* (APP11 JUMBF), data after EOI.
* PNG   -- chunk walk with CRC verification, text chunks (zTXt/iTXt inflated
           under a 64 KiB cap), eXIf, tIME, C2PA `caBX` presence, data after
           IEND, and a pixel decode for copy-move block matching.
* GIF / WebP -- dimensions only.

Not implemented (listed in every result's `not_performed`): lighting
consistency, edge-artifact analysis, double-JPEG-compression statistics,
C2PA signature validation, and pixel analysis of JPEG in this reference engine
(the browser console decodes JPEG pixels with the canvas API instead).
"""
from __future__ import annotations

import re
import struct
import zlib
from fractions import Fraction

from . import vocab
from .indicators import (
    Indicator,
    parse_error_indicator,
    parse_message,
    quote,
    software_indicators,
    trailing_data_indicator,
)

ANALYZER = "image@" + vocab.ENGINE_VERSION

MAX_TEXT_INFLATE = 64 * 1024
MAX_PIXELS = 16_000_000
PIXEL_ANALYSIS_BUDGET = 600_000
CLONE_BLOCK = 8
CLONE_MIN_BLOCKS = 32
CLONE_MIN_SHIFT = 16
CLONE_MAX_BUCKET = 8
CLONE_MIN_VARIANCE = 25

NOT_PERFORMED = [
    "Lighting and shadow consistency analysis (not implemented)",
    "Edge and compositing-boundary analysis (not implemented)",
    "Double-JPEG-compression statistics (not implemented)",
    "C2PA / Content Credentials signature validation (not implemented; presence only)",
    "Generative-model classifier (not implemented; no model is bundled or called)",
]

# ITU-T T.81 Annex K.1 luminance table, natural (row-major) order.
IJG_LUMA = (
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99,
)
ZIGZAG = (
    0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13, 6, 7, 14, 21, 28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37,
    44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63,
)
SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}

EXIF_TAGS = {
    0x010F: "Make", 0x0110: "Model", 0x0112: "Orientation", 0x0131: "Software",
    0x0132: "DateTime", 0x9003: "DateTimeOriginal", 0x9004: "DateTimeDigitized",
    0x9010: "OffsetTime", 0x9011: "OffsetTimeOriginal", 0xA002: "PixelXDimension",
    0xA003: "PixelYDimension",
}
GPS_TAGS = {1: "GPSLatitudeRef", 2: "GPSLatitude", 3: "GPSLongitudeRef", 4: "GPSLongitude"}
TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}


class ParseError(ValueError):
    pass


# --------------------------------------------------------------------------
# EXIF (TIFF structure)
# --------------------------------------------------------------------------
def parse_exif(tiff: bytes) -> dict:
    """Parse a TIFF/EXIF block. Every offset is bounds-checked; loops refused."""
    if len(tiff) < 8:
        raise ParseError("EXIF block shorter than a TIFF header")
    if tiff[:2] == b"II":
        end = "<"
    elif tiff[:2] == b"MM":
        end = ">"
    else:
        raise ParseError("EXIF block has no TIFF byte-order mark")
    if struct.unpack(end + "H", tiff[2:4])[0] != 42:
        raise ParseError("EXIF TIFF magic is not 42")
    out: dict = {}
    visited: set[int] = set()

    def read_ifd(offset: int, names: dict[int, str]) -> dict[int, int]:
        pointers: dict[int, int] = {}
        if offset in visited:
            raise ParseError("EXIF IFD loop")
        visited.add(offset)
        if offset + 2 > len(tiff):
            raise ParseError("EXIF IFD offset out of range")
        (count,) = struct.unpack(end + "H", tiff[offset:offset + 2])
        if count > 512:
            raise ParseError("EXIF IFD has an implausible entry count")
        for i in range(count):
            pos = offset + 2 + 12 * i
            if pos + 12 > len(tiff):
                raise ParseError("EXIF IFD entry out of range")
            tag, typ, n = struct.unpack(end + "HHI", tiff[pos:pos + 8])
            size = TYPE_SIZES.get(typ, 0) * n
            if size == 0:
                continue
            if size <= 4:
                raw = tiff[pos + 8:pos + 8 + size]
            else:
                (ptr,) = struct.unpack(end + "I", tiff[pos + 8:pos + 12])
                if ptr + size > len(tiff):
                    raise ParseError("EXIF value out of range")
                raw = tiff[ptr:ptr + size]
            if tag in (0x8769, 0x8825) and typ == 4:
                pointers[tag] = struct.unpack(end + "I", raw[:4])[0]
                continue
            name = names.get(tag)
            if name is None:
                continue
            out[name] = _exif_value(raw, typ, n, end)
        return pointers

    (ifd0,) = struct.unpack(end + "I", tiff[4:8])
    ptrs = read_ifd(ifd0, EXIF_TAGS)
    if 0x8769 in ptrs:
        read_ifd(ptrs[0x8769], EXIF_TAGS)
    if 0x8825 in ptrs:
        read_ifd(ptrs[0x8825], GPS_TAGS)
    return out


def _exif_value(raw: bytes, typ: int, n: int, end: str):
    if typ == 2:
        return raw.split(b"\x00", 1)[0].decode("latin-1").strip()
    if typ == 3:
        vals = struct.unpack(end + "H" * n, raw)
        return vals[0] if n == 1 else list(vals)
    if typ in (4, 9):
        vals = struct.unpack(end + ("I" if typ == 4 else "i") * n, raw)
        return vals[0] if n == 1 else list(vals)
    if typ in (5, 10):
        vals = struct.unpack(end + ("I" if typ == 5 else "i") * (2 * n), raw)
        return [[vals[2 * i], vals[2 * i + 1]] for i in range(n)]
    return None


def gps_decimal(exif: dict) -> str:
    """'lat,lon' to five decimals, computed with exact rationals."""
    def coord(key: str, ref_key: str, neg: str) -> str | None:
        parts = exif.get(key)
        if not isinstance(parts, list) or len(parts) != 3:
            return None
        if any(d == 0 for _, d in parts):
            return None
        value = sum(Fraction(n, d) / div for (n, d), div in zip(parts, (1, 60, 3600)))
        scaled = (value * 100000 * 2 + 1) // 2  # half-up
        units = int(scaled)
        sign = "-" if exif.get(ref_key, "") == neg else ""
        return f"{sign}{units // 100000}.{units % 100000:05d}"

    lat = coord("GPSLatitude", "GPSLatitudeRef", "S")
    lon = coord("GPSLongitude", "GPSLongitudeRef", "W")
    return f"{lat},{lon}" if lat and lon else ""


def exif_time_iso(value: str) -> str:
    """'2026:03:14 21:43:02' -> '2026-03-14T21:43:02' (no zone: EXIF has none)."""
    m = re.fullmatch(r"(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})", value or "")
    if not m:
        return ""
    y, mo, d, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}"


# --------------------------------------------------------------------------
# JPEG
# --------------------------------------------------------------------------
def ijg_quality(zigzag_values: list[int]) -> dict:
    natural = [0] * 64
    for k, v in enumerate(zigzag_values):
        natural[ZIGZAG[k]] = v
    best_q, best_diff = 0, None
    for q in range(1, 101):
        scale = 5000 // q if q < 50 else 200 - 2 * q
        diff = 0
        for i in range(64):
            t = (IJG_LUMA[i] * scale + 50) // 100
            t = 1 if t < 1 else 255 if t > 255 else t
            diff += abs(t - natural[i])
        if best_diff is None or diff < best_diff:
            best_q, best_diff = q, diff
    return {"quality": best_q, "abs_deviation": best_diff, "exact": best_diff == 0}


def parse_jpeg(data: bytes) -> dict:
    n = len(data)
    info: dict = {"format": "jpeg", "segments": [], "exif": {}, "xmp_creator_tool": "",
                  "quant_tables": {}, "c2pa_manifest": False, "frames": [], "eoi_offset": None,
                  "trailing_bytes": 0, "app13_photoshop": False, "parse_error": ""}
    pos = 2
    try:
        while pos + 2 <= n:
            if data[pos] != 0xFF:
                raise ParseError(f"expected a marker at offset {pos}")
            marker = data[pos + 1]
            if marker == 0xFF:
                pos += 1
                continue
            if marker == 0xD9:
                info["eoi_offset"] = pos
                break
            if 0xD0 <= marker <= 0xD7 or marker == 0x01:
                pos += 2
                continue
            if pos + 4 > n:
                raise ParseError("segment header truncated")
            (length,) = struct.unpack(">H", data[pos + 2:pos + 4])
            if length < 2 or pos + 2 + length > n:
                raise ParseError(f"segment 0x{marker:02X} length out of range")
            payload = data[pos + 4:pos + 2 + length]
            info["segments"].append({"marker": f"0x{marker:02X}", "length": length})
            _jpeg_segment(marker, payload, info)
            pos += 2 + length
            if marker == 0xDA:
                while True:
                    nxt = data.find(b"\xff", pos)
                    if nxt < 0 or nxt + 1 >= n:
                        pos = n
                        break
                    follow = data[nxt + 1]
                    if follow == 0x00 or 0xD0 <= follow <= 0xD7:
                        pos = nxt + 2
                        continue
                    pos = nxt
                    break
        if info["eoi_offset"] is None:
            raise ParseError("no end-of-image marker")
        info["trailing_bytes"] = n - (info["eoi_offset"] + 2)
    except (ParseError, struct.error) as exc:
        info["parse_error"] = parse_message(exc)
    return info


def _jpeg_segment(marker: int, payload: bytes, info: dict) -> None:
    if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
        try:
            info["exif"] = parse_exif(payload[6:])
        except (ParseError, struct.error) as exc:
            info["exif_error"] = str(exc)
    elif marker == 0xE1 and payload.startswith(b"http://ns.adobe.com/xap/1.0/\x00"):
        text = payload[29:].decode("utf-8", "replace")
        m = (re.search(r'CreatorTool="([^"]{1,200})"', text)
             or re.search(r"<xmp:CreatorTool>([^<]{1,200})</xmp:CreatorTool>", text))
        if m:
            info["xmp_creator_tool"] = m.group(1)
    elif marker == 0xEB and b"c2pa" in payload:
        info["c2pa_manifest"] = True
    elif marker == 0xED and payload.startswith(b"Photoshop 3.0"):
        info["app13_photoshop"] = True
    elif marker == 0xDB:
        i = 0
        while i < len(payload):
            pq, tq = payload[i] >> 4, payload[i] & 0x0F
            width = 2 if pq else 1
            end = i + 1 + 64 * width
            if end > len(payload):
                raise ParseError("DQT table truncated")
            if width == 1:
                vals = list(payload[i + 1:end])
            else:
                vals = list(struct.unpack(">" + "H" * 64, payload[i + 1:end]))
            info["quant_tables"][str(tq)] = vals
            i = end
    elif marker in SOF_MARKERS:
        if len(payload) < 6:
            raise ParseError("SOF segment truncated")
        _, h, w, comps = struct.unpack(">BHHB", payload[:6])
        info["frames"].append({"sof": f"0x{marker:02X}", "width": w, "height": h,
                               "components": comps})


# --------------------------------------------------------------------------
# PNG
# --------------------------------------------------------------------------
def parse_png(data: bytes) -> dict:
    info: dict = {"format": "png", "chunks": [], "ihdr": {}, "text": {}, "exif": {},
                  "time": "", "c2pa_manifest": False, "crc_errors": [], "trailing_bytes": 0,
                  "idat": b"", "parse_error": ""}
    pos, n = 8, len(data)
    idat = bytearray()
    seen_iend = False
    try:
        while pos + 12 <= n:
            length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
            name = ctype.decode("latin-1")
            if pos + 12 + length > n:
                raise ParseError(f"chunk {quote(name)} runs past the end of the file")
            body = data[pos + 8:pos + 8 + length]
            (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
            if zlib.crc32(ctype + body) & 0xFFFFFFFF != crc:
                info["crc_errors"].append(name)
            info["chunks"].append({"type": name, "length": length})
            if len(info["chunks"]) > 100_000:
                raise ParseError("implausible chunk count")
            _png_chunk(name, body, info, idat)
            pos += 12 + length
            if name == "IEND":
                seen_iend = True
                break
        if not seen_iend:
            raise ParseError("no IEND chunk")
        info["trailing_bytes"] = n - pos
    except (ParseError, struct.error) as exc:
        info["parse_error"] = parse_message(exc)
    info["idat"] = bytes(idat)
    return info


def _inflate_capped(blob: bytes) -> tuple[str, bool]:
    d = zlib.decompressobj()
    try:
        out = d.decompress(blob, MAX_TEXT_INFLATE)
    except zlib.error:
        return "", False
    return out.decode("latin-1", "replace"), bool(d.unconsumed_tail)


def _png_chunk(name: str, body: bytes, info: dict, idat: bytearray) -> None:
    if name == "IHDR":
        if len(body) != 13:
            raise ParseError("IHDR is not 13 bytes")
        w, h, depth, color, comp, filt, interlace = struct.unpack(">IIBBBBB", body)
        info["ihdr"] = {"width": w, "height": h, "bit_depth": depth, "color_type": color,
                        "interlace": interlace}
    elif name == "IDAT":
        idat.extend(body)
    elif name == "tEXt" and b"\x00" in body:
        key, value = body.split(b"\x00", 1)
        info["text"][key.decode("latin-1")[:79]] = value.decode("latin-1")[:4000]
    elif name == "zTXt" and b"\x00" in body:
        key, rest = body.split(b"\x00", 1)
        text, truncated = _inflate_capped(rest[1:])
        info["text"][key.decode("latin-1")[:79]] = text[:4000]
        if truncated:
            info.setdefault("inflate_capped", []).append(key.decode("latin-1")[:79])
    elif name == "iTXt" and b"\x00" in body:
        key, rest = body.split(b"\x00", 1)
        if len(rest) >= 2:
            flag = rest[0]
            parts = rest[2:].split(b"\x00", 2)
            if len(parts) == 3:
                raw = parts[2]
                text = _inflate_capped(raw)[0] if flag else raw.decode("utf-8", "replace")
                info["text"][key.decode("latin-1")[:79]] = text[:4000]
    elif name == "eXIf":
        try:
            info["exif"] = parse_exif(body)
        except (ParseError, struct.error) as exc:
            info["exif_error"] = str(exc)
    elif name == "tIME" and len(body) == 7:
        y, mo, d, h, mi, s = struct.unpack(">HBBBBB", body)
        info["time"] = f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{s:02d}Z"
    elif name == "caBX":
        info["c2pa_manifest"] = True


def decode_png_gray(info: dict) -> tuple[int, int, bytearray] | tuple[None, None, str]:
    """8-bit gray/RGB/gray+alpha/RGBA, non-interlaced -> luminance bytes.

    The inflate output is capped at the size IHDR declares, so a
    decompression bomb stops at the declared image size.
    """
    ihdr = info.get("ihdr") or {}
    w, h = ihdr.get("width", 0), ihdr.get("height", 0)
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(ihdr.get("color_type", -1))
    if not channels or ihdr.get("bit_depth") != 8:
        return None, None, "pixel analysis supports 8-bit gray, gray+alpha, RGB and RGBA PNG"
    if ihdr.get("interlace"):
        return None, None, "interlaced PNG is not decoded"
    if w <= 0 or h <= 0 or w * h > MAX_PIXELS:
        return None, None, f"image dimensions exceed the {MAX_PIXELS}-pixel decode limit"
    stride = w * channels
    expected = (stride + 1) * h
    d = zlib.decompressobj()
    try:
        raw = d.decompress(info["idat"], expected + 1)
    except zlib.error:
        return None, None, "IDAT inflate failed"
    if len(raw) > expected or d.unconsumed_tail:
        return None, None, "IDAT inflates past the declared image size (decompression bomb guard)"
    if len(raw) < expected:
        return None, None, "IDAT is shorter than the declared image size"
    out = bytearray(w * h)
    prev = bytearray(stride)
    for y in range(h):
        base = y * (stride + 1)
        ftype = raw[base]
        line = bytearray(raw[base + 1:base + 1 + stride])
        _unfilter(ftype, line, prev, channels)
        row = y * w
        if channels in (1, 2):
            for x in range(w):
                out[row + x] = line[x * channels]
        else:
            for x in range(w):
                i = x * channels
                out[row + x] = (299 * line[i] + 587 * line[i + 1] + 114 * line[i + 2]) // 1000
        prev = line
    return w, h, out


def _unfilter(ftype: int, line: bytearray, prev: bytearray, bpp: int) -> None:
    n = len(line)
    if ftype == 0:
        return
    if ftype == 1:
        for i in range(bpp, n):
            line[i] = (line[i] + line[i - bpp]) & 0xFF
    elif ftype == 2:
        for i in range(n):
            line[i] = (line[i] + prev[i]) & 0xFF
    elif ftype == 3:
        for i in range(n):
            left = line[i - bpp] if i >= bpp else 0
            line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
    elif ftype == 4:
        for i in range(n):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pred = a if pa <= pb and pa <= pc else b if pb <= pc else c
            line[i] = (line[i] + pred) & 0xFF
    else:
        raise ParseError(f"unknown PNG filter type {ftype}")


# --------------------------------------------------------------------------
# Copy-move (cloned region) block matching
# --------------------------------------------------------------------------
def copy_move(width: int, height: int, gray: bytes | bytearray) -> dict:
    """Find groups of identical, non-flat 8x8 blocks sharing one displacement.

    Pixels are quantized to 64 levels (value >> 2). Blocks with per-pixel
    variance below CLONE_MIN_VARIANCE are skipped (flat sky, walls); keys seen
    more than CLONE_MAX_BUCKET times are skipped (tiles, text). A displacement
    shared by at least CLONE_MIN_BLOCKS block pairs is reported.
    """
    b = CLONE_BLOCK
    if width < 2 * b or height < 2 * b:
        return {"clusters": [], "blocks_examined": 0, "note": "image too small"}
    q = bytes(v >> 2 for v in gray)
    # Integral images of the quantized values and their squares.
    iw = width + 1
    s1 = [0] * (iw * (height + 1))
    s2 = [0] * (iw * (height + 1))
    for y in range(height):
        r1 = r2 = 0
        row = y * width
        for x in range(width):
            v = q[row + x]
            r1 += v
            r2 += v * v
            s1[(y + 1) * iw + x + 1] = s1[y * iw + x + 1] + r1
            s2[(y + 1) * iw + x + 1] = s2[y * iw + x + 1] + r2
    n = b * b
    min_var = CLONE_MIN_VARIANCE >> 4  # variance scales by 1/16 after >> 2
    rows = [q[y * width:(y + 1) * width] for y in range(height)]
    buckets: dict[int, list[tuple[int, int]]] = {}
    examined = 0
    for y in range(height - b + 1):
        y2 = y + b
        for x in range(width - b + 1):
            x2 = x + b
            t1 = s1[y2 * iw + x2] - s1[y * iw + x2] - s1[y2 * iw + x] + s1[y * iw + x]
            t2 = s2[y2 * iw + x2] - s2[y * iw + x2] - s2[y2 * iw + x] + s2[y * iw + x]
            if n * t2 - t1 * t1 < min_var * n * n:
                continue
            examined += 1
            key = hash(b"".join(rows[y + i][x:x2] for i in range(b)))
            buckets.setdefault(key, []).append((x, y))
    shifts: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for positions in buckets.values():
        if len(positions) < 2 or len(positions) > CLONE_MAX_BUCKET:
            continue
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                (ax, ay), (bx, by) = positions[i], positions[j]
                dx, dy = bx - ax, by - ay
                if dx < 0 or (dx == 0 and dy < 0):
                    dx, dy, ax, ay = -dx, -dy, bx, by
                if abs(dx) + abs(dy) < CLONE_MIN_SHIFT:
                    continue
                shifts.setdefault((dx, dy), []).append((ax, ay))
    clusters = []
    for (dx, dy), sources in shifts.items():
        if len(sources) < CLONE_MIN_BLOCKS:
            continue
        xs = [p[0] for p in sources]
        ys = [p[1] for p in sources]
        src = [min(xs), min(ys), max(xs) + b, max(ys) + b]
        clusters.append({
            "shift": [dx, dy],
            "matched_blocks": len(sources),
            "region_a": src,
            "region_b": [src[0] + dx, src[1] + dy, src[2] + dx, src[3] + dy],
        })
    clusters.sort(key=lambda c: (-c["matched_blocks"], c["shift"][0], c["shift"][1]))
    return {"clusters": clusters[:8], "blocks_examined": examined, "note": ""}


def dhash(width: int, height: int, gray: bytes | bytearray) -> str:
    """64-bit difference hash: 9x8 box-averaged grid, left < right per row."""
    if width < 9 or height < 8:
        return ""
    cells = []
    for cy in range(8):
        y0, y1 = cy * height // 8, (cy + 1) * height // 8
        row = []
        for cx in range(9):
            x0, x1 = cx * width // 9, (cx + 1) * width // 9
            total = 0
            for y in range(y0, y1):
                base = y * width
                total += sum(gray[base + x0:base + x1])
            row.append(total // ((y1 - y0) * (x1 - x0)))
        cells.append(row)
    bits = 0
    for row in cells:
        for x in range(8):
            bits = (bits << 1) | (1 if row[x] < row[x + 1] else 0)
    return f"{bits:016x}"


def hamming_hex(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def downscale_gray(width: int, height: int, gray: bytes | bytearray) -> tuple[int, int, bytearray, int]:
    """Integer box-downscale so pixel analysis stays inside its budget."""
    factor = 1
    while (width // factor) * (height // factor) > PIXEL_ANALYSIS_BUDGET:
        factor += 1
    if factor == 1:
        return width, height, bytearray(gray), 1
    w2, h2 = width // factor, height // factor
    out = bytearray(w2 * h2)
    area = factor * factor
    for y in range(h2):
        for x in range(w2):
            total = 0
            for yy in range(y * factor, y * factor + factor):
                base = yy * width + x * factor
                total += sum(gray[base:base + factor])
            out[y * w2 + x] = total // area
    return w2, h2, out, factor


# --------------------------------------------------------------------------
# Indicators and observations
# --------------------------------------------------------------------------
def _metadata_indicators(exif: dict, actual_dims: tuple[int, int] | None,
                         software_fields: list[tuple[str, str]]) -> list[Indicator]:
    out: list[Indicator] = []
    for field_name, value in software_fields:
        if value:
            out.extend(software_indicators(field_name, value, ANALYZER))
    modified = exif.get("DateTime", "")
    original = exif.get("DateTimeOriginal", "")
    if modified and original and modified != original:
        out.append(Indicator(
            code="METADATA.TIMESTAMP_MISMATCH",
            category="METADATA",
            title="Modification time differs from capture time",
            evidence=f"EXIF DateTime = {quote(modified)}; DateTimeOriginal = {quote(original)}",
            method="Comparison of EXIF IFD0 DateTime with Exif IFD DateTimeOriginal.",
            confidence="MODERATE",
            limitation=(
                "Both values are unsigned metadata that any tool can rewrite. The gap shows the "
                "file was written after capture, not what changed."
            ),
            alternatives=(
                "In-camera or phone-gallery edit",
                "Export or re-save by photo-management software",
                "Camera clock or time-zone adjustment",
            ),
            state=vocab.REVIEW_REQUIRED,
            analyzer=ANALYZER,
        ))
    px, py = exif.get("PixelXDimension"), exif.get("PixelYDimension")
    if actual_dims and isinstance(px, int) and isinstance(py, int) and px and py:
        w, h = actual_dims
        if (px, py) not in ((w, h), (h, w)):
            out.append(Indicator(
                code="METADATA.DIMENSION_MISMATCH",
                category="METADATA",
                title="Recorded pixel dimensions differ from the image's actual dimensions",
                evidence=f"EXIF says {px}x{py}; the encoded image is {w}x{h}",
                method="Comparison of Exif PixelX/YDimension with the frame header.",
                confidence="MODERATE",
                limitation="Consistent with resizing or cropping; says nothing about content.",
                alternatives=(
                    "Resize or crop after capture",
                    "Metadata copied from a different rendition",
                ),
                state=vocab.REVIEW_REQUIRED,
                analyzer=ANALYZER,
            ))
    if not exif:
        out.append(Indicator(
            code="PROVENANCE.NO_CAPTURE_METADATA",
            category="PROVENANCE",
            title="No camera metadata present",
            evidence="No EXIF block was found in the file",
            method="Container parse for EXIF (APP1 in JPEG, eXIf in PNG).",
            confidence="HIGH",
            limitation=(
                "Most social and messaging platforms strip EXIF. Absence is a provenance gap, "
                "not a sign of manipulation."
            ),
            alternatives=(
                "Platform metadata stripping",
                "Screenshot or screen recording",
                "Privacy tool or deliberate removal",
            ),
            state=vocab.PROVENANCE_GAP,
            analyzer=ANALYZER,
        ))
    return out


def _c2pa_indicator(where: str) -> Indicator:
    return Indicator(
        code="PROVENANCE.C2PA_MANIFEST_PRESENT",
        category="PROVENANCE",
        title="Content Credentials (C2PA) manifest data detected — not validated",
        evidence=f"C2PA manifest store bytes found in {where}",
        method="Container scan for the C2PA JUMBF label.",
        confidence="HIGH",
        limitation=(
            "This engine has no C2PA validator. The signature, signer and assertions were not "
            "checked, so the manifest supports nothing until a validator confirms it."
        ),
        alternatives=(
            "A valid manifest from a capture device or editor",
            "A manifest copied from another file (would fail hash binding)",
        ),
        state=vocab.INCONCLUSIVE,
        analyzer=ANALYZER,
    )


def _clone_indicator(cluster: dict, factor: int) -> Indicator:
    a, b = cluster["region_a"], cluster["region_b"]
    scale = f" (analysed at 1/{factor} scale)" if factor > 1 else ""
    return Indicator(
        code="SPATIAL.COPY_MOVE",
        category="SPATIAL",
        title="Duplicated image region (possible copy-move)",
        evidence=(
            f"{cluster['matched_blocks']} identical non-flat 8x8 blocks shifted by "
            f"({cluster['shift'][0]}, {cluster['shift'][1]}) px; region {a} matches region "
            f"{b}{scale}"
        ),
        method="Exact block matching on 6-bit luminance with flat-block and texture filters.",
        confidence="MODERATE",
        limitation=(
            "Cannot tell which region is the source. Misses scaled, rotated or recompressed "
            "clones, and lossy JPEG usually defeats exact matching."
        ),
        alternatives=(
            "Genuinely repetitive content (tiles, windows, printed patterns)",
            "Synthetic or graphic imagery",
            "Panorama or HDR stitching",
        ),
        state=vocab.ANOMALY_DETECTED,
        analyzer=ANALYZER,
        location=f"{a} -> {b}",
    )


def analyze_image(data: bytes, mime: str) -> dict:
    """Return {'metadata', 'indicators', 'observations', 'not_performed', ...}."""
    result: dict = {"analyzer": ANALYZER, "metadata": {}, "indicators": [],
                    "observations": [], "not_performed": list(NOT_PERFORMED), "pixels": None}
    inds: list[Indicator] = result["indicators"]
    if mime == "image/jpeg":
        info = parse_jpeg(data)
        frame = info["frames"][0] if info["frames"] else None
        dims = (frame["width"], frame["height"]) if frame else None
        q = info["quant_tables"].get("0")
        result["metadata"] = {
            "format": "jpeg",
            "dimensions": list(dims) if dims else None,
            "exif": info["exif"],
            "xmp_creator_tool": info["xmp_creator_tool"],
            "segments": len(info["segments"]),
            "quantization": ijg_quality(q) if q and len(q) == 64 else None,
            "c2pa_manifest": info["c2pa_manifest"],
            "trailing_bytes": info["trailing_bytes"],
        }
        if info["parse_error"]:
            inds.append(parse_error_indicator(info["parse_error"], ANALYZER))
        inds.extend(_metadata_indicators(
            info["exif"], dims,
            [("EXIF Software", str(info["exif"].get("Software", ""))),
             ("XMP CreatorTool", info["xmp_creator_tool"])]))
        if info["c2pa_manifest"]:
            inds.append(_c2pa_indicator("an APP11 segment"))
        if info["trailing_bytes"] > 0:
            inds.append(trailing_data_indicator(info["trailing_bytes"], "JPEG EOI", ANALYZER))
        result["not_performed"].append(
            "Copy-move pixel analysis of JPEG (browser console only; needs a JPEG decoder)")
        exif = info["exif"]
    elif mime == "image/png":
        info = parse_png(data)
        ihdr = info["ihdr"]
        dims = (ihdr["width"], ihdr["height"]) if ihdr else None
        result["metadata"] = {
            "format": "png",
            "dimensions": list(dims) if dims else None,
            "exif": info["exif"],
            "text": info["text"],
            "png_time": info["time"],
            "chunks": len(info["chunks"]),
            "crc_errors": info["crc_errors"],
            "c2pa_manifest": info["c2pa_manifest"],
            "trailing_bytes": info["trailing_bytes"],
        }
        if info["parse_error"]:
            inds.append(parse_error_indicator(info["parse_error"], ANALYZER))
        if info["crc_errors"]:
            inds.append(Indicator(
                code="CONTAINER.CRC_MISMATCH",
                category="CONTAINER",
                title="PNG chunk checksum does not match its contents",
                evidence=f"CRC-32 mismatch in chunk(s): {', '.join(info['crc_errors'])}",
                method="CRC-32 recomputed over each chunk type and body.",
                confidence="HIGH",
                limitation=(
                    "Proves the bytes changed after the chunk was written, or were corrupted. "
                    "Does not show whether the change was deliberate."
                ),
                alternatives=("Storage or transfer corruption", "Byte-level editing"),
                state=vocab.ANOMALY_DETECTED,
                analyzer=ANALYZER,
            ))
        software_fields = [("EXIF Software", str(info["exif"].get("Software", "")))]
        software_fields += [(f"PNG text '{k}'", v) for k, v in sorted(info["text"].items())
                            if k.lower() in ("software", "comment", "description", "source")]
        inds.extend(_metadata_indicators(info["exif"], dims, software_fields))
        if "parameters" in info["text"]:
            inds.append(Indicator(
                code="SYNTHETIC.GENERATION_PARAMETERS",
                category="SYNTHETIC",
                title="Text chunk named 'parameters' present",
                evidence=f"PNG text chunk 'parameters' ({len(info['text']['parameters'])} chars)",
                method="PNG text-chunk keyword inspection.",
                confidence="MODERATE",
                limitation=(
                    "Some diffusion front-ends store generation settings under this keyword. "
                    "Any tool can write it, and it is lost on re-save."
                ),
                alternatives=("An unrelated tool using the same keyword",),
                state=vocab.REVIEW_REQUIRED,
                analyzer=ANALYZER,
            ))
        if info["c2pa_manifest"]:
            inds.append(_c2pa_indicator("a caBX chunk"))
        if info["trailing_bytes"] > 0:
            inds.append(trailing_data_indicator(info["trailing_bytes"], "PNG IEND", ANALYZER))
        if not info["parse_error"]:
            w, h, gray = decode_png_gray(info)
            if w is None:
                result["not_performed"].append(f"Copy-move pixel analysis ({gray})")
            else:
                w2, h2, small, factor = downscale_gray(w, h, gray)
                cm = copy_move(w2, h2, small)
                result["pixels"] = {"width": w, "height": h, "analysis_scale": factor,
                                    "blocks_examined": cm["blocks_examined"],
                                    "clone_clusters": cm["clusters"],
                                    "dhash": dhash(w, h, gray)}
                for cluster in cm["clusters"]:
                    inds.append(_clone_indicator(cluster, factor))
        exif = info["exif"]
    else:
        exif = {}
        result["metadata"] = {"format": mime.split("/")[-1]}
        result["not_performed"].append(f"Structural analysis of {mime} (not implemented)")
    # Observations for claim assessment: what the metadata *says*.
    when = exif_time_iso(str(exif.get("DateTimeOriginal", "")))
    if when:
        result["observations"].append({"dimension": "time", "value": when,
                                       "basis": "EXIF DateTimeOriginal (unsigned metadata)"})
    device = " ".join(str(exif.get(k, "")).strip() for k in ("Make", "Model")).strip()
    if device:
        result["observations"].append({"dimension": "device", "value": device,
                                       "basis": "EXIF Make/Model (unsigned metadata)"})
    gps = gps_decimal(exif)
    if gps:
        result["observations"].append({"dimension": "location", "value": gps,
                                       "basis": "EXIF GPS (unsigned metadata)"})
    return result
