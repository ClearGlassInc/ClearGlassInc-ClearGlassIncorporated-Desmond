# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Evidence intake: acquisition, hashing, type detection, safe boundaries.

Rules this module enforces:

* The file type comes from the bytes (magic numbers), never from the filename
  or a declared MIME type. A declared type that disagrees is recorded as an
  indicator, not trusted.
* Filenames are display labels only. They are sanitised and never used to open,
  write or route anything.
* Paths are resolved strictly: no symlinks, no non-regular files, no escape from
  an allowed root, no file over the size limit.
* Executables and archives are hashed and recorded but never parsed,
  decompressed or executed (`HASH_ONLY` boundary).
* URLs are recorded as references. Nothing here fetches them. `validate_url`
  exists so a future fetch adapter cannot be pointed at internal addresses.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import socket
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from . import vocab
from .canonical import canonical_json, digest, sha256_bytes

MAX_EVIDENCE_BYTES = 512 * 1024 * 1024   # hash-and-record ceiling
MAX_ANALYSIS_BYTES = 64 * 1024 * 1024    # parsers only see files up to this size
CHUNK = 1024 * 1024

HASH_ONLY_TYPES = {
    "application/x-executable", "application/x-dosexec", "application/x-mach-binary",
    "application/zip", "application/gzip", "application/x-7z-compressed",
    "application/x-rar-compressed", "application/x-sh",
}


class IntakeError(ValueError):
    """Evidence refused at the boundary. The message names the rule."""


def sniff_mime(head: bytes) -> str:
    """Media type from leading bytes. Unknown binary is octet-stream."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and len(head) >= 12:
        kind = head[8:12]
        if kind == b"WEBP":
            return "image/webp"
        if kind == b"WAVE":
            return "audio/wav"
        if kind == b"AVI ":
            return "video/x-msvideo"
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand == b"qt  ":
            return "video/quicktime"
        if brand in (b"M4A ", b"M4B "):
            return "audio/mp4"
        return "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    if head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0
                                   and head[1] & 0x06 != 0):
        return "audio/mpeg"
    if head.startswith(b"fLaC"):
        return "audio/flac"
    if head.startswith(b"OggS"):
        return "application/ogg"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"PK\x03\x04"):
        return "application/zip"
    if head.startswith(b"\x1f\x8b"):
        return "application/gzip"
    if head.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "application/x-7z-compressed"
    if head.startswith(b"Rar!\x1a\x07"):
        return "application/x-rar-compressed"
    if head.startswith(b"\x7fELF"):
        return "application/x-executable"
    if head.startswith(b"MZ"):
        return "application/x-dosexec"
    if head[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe",
                    b"\xcf\xfa\xed\xfe"):
        return "application/x-mach-binary"
    if head.startswith(b"#!"):
        return "application/x-sh"
    if head and b"\x00" not in head[:4096]:
        try:
            text = head[:4096].decode("utf-8")
        except UnicodeDecodeError:
            # A multi-byte character cut at the 4 KiB boundary is still text.
            try:
                text = head[:4093].decode("utf-8")
            except UnicodeDecodeError:
                return "application/octet-stream"
        stripped = text.lstrip()
        if stripped[:1] in ("{", "["):
            try:
                json.loads(head.decode("utf-8"))
                return "application/json"
            except (UnicodeDecodeError, ValueError):
                pass
        return "text/plain"
    return "application/octet-stream"


def source_type_for(mime: str) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/") or mime == "application/ogg":
        return "audio"
    if mime == "application/json":
        return "event"
    if mime == "text/plain":
        return "text"
    return "document"


def processing_boundary(mime: str) -> str:
    return "HASH_ONLY" if mime in HASH_ONLY_TYPES else "PARSE"


_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def display_name(name: str | None) -> str:
    """A filename reduced to a harmless label. Never used as a path."""
    if not name:
        return ""
    name = unicodedata.normalize("NFC", str(name))
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = _CONTROL.sub("", name).strip()
    if name in (".", ".."):
        return ""
    return name[:120]


def safe_open_path(path: str | os.PathLike, root: str | os.PathLike | None = None,
                   max_bytes: int = MAX_EVIDENCE_BYTES) -> Path:
    """Resolve an evidence path under the intake rules, or raise IntakeError."""
    raw = Path(path)
    try:
        st = os.lstat(raw)
    except FileNotFoundError as exc:
        raise IntakeError(f"no such file: {display_name(str(path))}") from exc
    if stat.S_ISLNK(st.st_mode):
        raise IntakeError("symbolic links are refused: acquire the target file directly")
    if not stat.S_ISREG(st.st_mode):
        raise IntakeError("only regular files are accepted as evidence")
    resolved = raw.resolve(strict=True)
    if root is not None:
        base = Path(root).resolve(strict=True)
        if resolved != base and base not in resolved.parents:
            raise IntakeError("path escapes the evidence root (path traversal refused)")
    if st.st_size > max_bytes:
        raise IntakeError(f"file exceeds the {max_bytes}-byte evidence limit")
    return resolved


# --------------------------------------------------------------------------
# URL references (never fetched here)
# --------------------------------------------------------------------------
_BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa", ".corp")
_NUMERIC_HOST = re.compile(r"^(0x[0-9a-f]+|[0-9]+)(\.(0x[0-9a-f]+|[0-9]+))*$", re.I)


def _q(value: str) -> str:
    from .indicators import quote

    return quote(value)


def _ip_is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
                or ip.is_reserved or ip.is_unspecified or not ip.is_global)


def validate_url(url: str, *, resolve: bool = False) -> tuple[bool, list[str]]:
    """Decide whether a URL is safe for a (future) fetch adapter.

    Returns (fetchable, reasons). A URL can still be *recorded* as a reference
    when it is not fetchable; the reasons say why no adapter may request it.
    With resolve=True every resolved address must be public. DNS can change
    between this check and a request (rebinding), so an adapter must connect to
    the address it checked, not re-resolve the name.
    """
    reasons: list[str] = []
    if not isinstance(url, str) or not url or len(url) > 2048:
        return False, ["URL is empty or longer than 2048 characters"]
    if _CONTROL.search(url) or " " in url:
        return False, ["URL contains whitespace or control characters"]
    parts = urlsplit(url)
    if parts.scheme.lower() != "https":
        reasons.append(f"scheme {_q(parts.scheme or '(none)')} is not https")
    if parts.username or parts.password:
        reasons.append("credentials in the URL are refused")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        reasons.append("URL has no host")
        return False, reasons
    try:
        port = parts.port
    except ValueError:
        reasons.append("port is not a number")
        port = None
    if port not in (None, 443):
        reasons.append(f"port {port} is not 443")
    if host == "localhost" or host.endswith(_BLOCKED_HOST_SUFFIXES):
        reasons.append(f"host {_q(host)} is an internal name")
    try:
        literal = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        literal = None
        if _NUMERIC_HOST.match(host):
            reasons.append("numeric or hex host encodings are refused")
    if literal is not None and not _ip_is_public(literal):
        reasons.append(f"address {literal} is not publicly routable")
    if resolve and literal is None and not reasons:
        try:
            infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        except OSError:
            reasons.append("host did not resolve")
        else:
            for info in infos:
                addr = ipaddress.ip_address(info[4][0])
                if not _ip_is_public(addr):
                    reasons.append(f"host resolves to non-public address {addr}")
                    break
    return (not reasons), reasons


# --------------------------------------------------------------------------
# Acquisition records
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    label: str
    source_type: str
    object_kind: str
    content_sha256: str
    size_bytes: int
    mime_sniffed: str
    mime_declared: str
    declared_name: str
    acquired_at: str
    acquired_by: str
    acquisition_method: str
    processing_boundary: str
    provenance_state: str
    parent_id: str = ""
    transformation: str = ""
    upstream_source: str = ""
    demonstration: bool = False

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def evidence_id_for(content_sha256: str, acquired_at: str, label: str) -> str:
    return "EV-" + digest({"sha256": content_sha256, "at": acquired_at, "label": label})[:12].upper()


def acquire_bytes(data: bytes, *, label: str, acquired_at: str, acquired_by: str,
                  declared_name: str = "", declared_mime: str = "", evidence_id: str = "",
                  method: str = "upload", object_kind: str = vocab.ORIGINAL,
                  parent_id: str = "", transformation: str = "", upstream_source: str = "",
                  demonstration: bool = False) -> EvidenceRecord:
    if not isinstance(data, (bytes, bytearray)):
        raise IntakeError("evidence content must be bytes")
    if len(data) > MAX_EVIDENCE_BYTES:
        raise IntakeError(f"evidence exceeds the {MAX_EVIDENCE_BYTES}-byte limit")
    if not acquired_by.strip():
        raise IntakeError("acquired_by is required for chain of custody")
    sha = sha256_bytes(bytes(data))
    mime = sniff_mime(bytes(data[:4096]))
    if object_kind == vocab.DERIVATIVE and not parent_id:
        raise IntakeError("a derivative must name its parent evidence")
    return EvidenceRecord(
        evidence_id=evidence_id or evidence_id_for(sha, acquired_at, label),
        label=label,
        source_type=source_type_for(mime),
        object_kind=object_kind,
        content_sha256=sha,
        size_bytes=len(data),
        mime_sniffed=mime,
        mime_declared=(declared_mime or "")[:100],
        declared_name=display_name(declared_name),
        acquired_at=acquired_at,
        acquired_by=acquired_by,
        acquisition_method=method,
        processing_boundary=processing_boundary(mime),
        provenance_state="DECLARED_DERIVATIVE" if parent_id else "ACQUIRED",
        parent_id=parent_id,
        transformation=transformation,
        upstream_source=upstream_source,
        demonstration=demonstration,
    )


def acquire_file(path: str | os.PathLike, *, root: str | os.PathLike | None = None,
                 **kwargs) -> tuple[EvidenceRecord, bytes | None]:
    """Hash a file in chunks. Returns the record and, when the file is small
    enough to analyse, its bytes (a read-only copy; the file is never written)."""
    resolved = safe_open_path(path, root)
    h = hashlib.sha256()
    size = 0
    keep = bytearray()
    with open(resolved, "rb") as fh:
        while True:
            chunk = fh.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
            if size <= MAX_ANALYSIS_BYTES:
                keep.extend(chunk)
    data = bytes(keep) if size <= MAX_ANALYSIS_BYTES else None
    head = bytes(keep[:4096])
    kwargs.setdefault("declared_name", resolved.name)
    kwargs.setdefault("label", display_name(resolved.name))
    if data is not None:
        record = acquire_bytes(data, method="file", **kwargs)
    else:
        mime = sniff_mime(head)
        record = EvidenceRecord(
            evidence_id=kwargs.get("evidence_id") or evidence_id_for(
                h.hexdigest(), kwargs["acquired_at"], kwargs["label"]),
            label=kwargs["label"], source_type=source_type_for(mime),
            object_kind=vocab.ORIGINAL, content_sha256=h.hexdigest(), size_bytes=size,
            mime_sniffed=mime, mime_declared=kwargs.get("declared_mime", ""),
            declared_name=display_name(kwargs["declared_name"]),
            acquired_at=kwargs["acquired_at"], acquired_by=kwargs["acquired_by"],
            acquisition_method="file", processing_boundary="HASH_ONLY",
            provenance_state="ACQUIRED",
        )
    return record, data


def acquire_text(text: str, **kwargs) -> tuple[EvidenceRecord, bytes]:
    data = text.encode("utf-8")
    return acquire_bytes(data, method="text-entry", **kwargs), data


def acquire_event(event: dict, **kwargs) -> tuple[EvidenceRecord, bytes]:
    """A structured event record, hashed in canonical JSON form."""
    if not isinstance(event, dict):
        raise IntakeError("a structured event must be a JSON object")
    data = canonical_json(event).encode("utf-8")
    return acquire_bytes(data, method="structured-event", **kwargs), data


def acquire_url_reference(url: str, **kwargs) -> tuple[EvidenceRecord, list[str]]:
    """Record a URL as a reference. The content is NOT acquired, so the record
    carries a provenance gap until someone captures the content itself."""
    fetchable, reasons = validate_url(url)
    data = url.encode("utf-8")
    record = acquire_bytes(data, method="url-reference", **kwargs)
    fields = record.to_dict()
    fields.update(source_type="url", mime_sniffed="text/uri-list",
                  processing_boundary="REFERENCE_ONLY", provenance_state=vocab.PROVENANCE_GAP)
    notes = ["URL recorded as a reference; its content was not fetched or acquired."]
    notes += ([] if fetchable else [f"not fetchable: {r}" for r in reasons])
    return EvidenceRecord(**fields), notes


def declared_mime_indicator(record: EvidenceRecord):
    """A declared type that disagrees with the bytes."""
    from .indicators import Indicator, quote

    declared = (record.mime_declared or "").split(";")[0].strip().lower()
    if not declared or declared == record.mime_sniffed:
        return None
    if declared in ("image/jpg",) and record.mime_sniffed == "image/jpeg":
        return None
    return Indicator(
        code="CONTAINER.TYPE_MISMATCH",
        category="CONTAINER",
        title="Declared file type disagrees with the file's bytes",
        evidence=f"declared {quote(declared)}; content signature is {quote(record.mime_sniffed)}",
        method="Magic-number signature comparison against the declared media type.",
        confidence="HIGH",
        limitation="Shows a labelling inconsistency, not how or why it arose.",
        alternatives=("Renamed file extension", "Misconfigured upload client"),
        state=vocab.REVIEW_REQUIRED,
        analyzer="intake@" + vocab.ENGINE_VERSION,
    )
