"""Secure browser intelligence assistant primitives for lawful defensive research.

This module is intentionally standard-library only so it can run in CI and in
restricted analyst workstations. Integrations with browsers, Foundry, Gotham,
AIP, and Apollo should wrap these deterministic controls rather than bypassing
citation, provenance, authorization, and audit requirements.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest
import base64
import json
import secrets
from urllib.parse import urlparse
from uuid import uuid4

from artemis.intelligence.platform import AccessContext, ImmutableAuditLog

PUBLIC_SCHEMES = frozenset({"http", "https"})
PRIVATE_HOST_PREFIXES = ("10.", "127.", "169.254.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.", "192.168.")
PRIVATE_HOSTS = frozenset({"localhost", "0.0.0.0", "::1"})


@dataclass(frozen=True)
class SourceRecord:
    """Public-source provenance captured from a browser tab or ingestion job."""

    source_id: str
    url: str
    title: str
    captured_at: datetime
    content_hash: str
    license_hint: str
    public_only: bool = True


@dataclass(frozen=True)
class BrowserTab:
    tab_id: str
    url: str
    title: str
    opened_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ResearchNote:
    note_id: str
    tab_id: str
    body: str
    source_ids: tuple[str, ...]
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class CitedClaim:
    text: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class SummaryArtifact:
    artifact_id: str
    title: str
    claims: tuple[CitedClaim, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SecretBox:
    """Password-derived local secret sealing for API keys and browser tokens.

    This is a portable reference implementation. Production desktop builds
    should bind the wrapping key to the OS keychain or hardware-backed keystore;
    ciphertext remains local-first and never enters model context.
    """

    def seal(self, plaintext: str, passphrase: str) -> dict[str, str]:
        if not passphrase:
            raise ValueError("passphrase is required")
        salt = secrets.token_bytes(16)
        key = pbkdf2_hmac("sha256", passphrase.encode(), salt, 210_000, dklen=32)
        nonce = secrets.token_bytes(32)
        stream = sha256(key + nonce).digest()
        payload = plaintext.encode("utf-8")
        ciphertext = bytes(byte ^ stream[index % len(stream)] for index, byte in enumerate(payload))
        tag = sha256(key + nonce + ciphertext).hexdigest()
        return {
            "kdf": "PBKDF2-HMAC-SHA256",
            "iterations": "210000",
            "salt": base64.b64encode(salt).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "tag": tag,
        }

    def open(self, sealed: dict[str, str], passphrase: str) -> str:
        salt = base64.b64decode(sealed["salt"])
        nonce = base64.b64decode(sealed["nonce"])
        ciphertext = base64.b64decode(sealed["ciphertext"])
        key = pbkdf2_hmac("sha256", passphrase.encode(), salt, int(sealed["iterations"]), dklen=32)
        expected_tag = sha256(key + nonce + ciphertext).hexdigest()
        if not compare_digest(expected_tag, sealed["tag"]):
            raise ValueError("secret authentication failed")
        stream = sha256(key + nonce).digest()
        plaintext = bytes(byte ^ stream[index % len(stream)] for index, byte in enumerate(ciphertext))
        return plaintext.decode("utf-8")


class PublicSourcePolicy:
    """Fail-closed URL policy for public OSINT ingestion."""

    def validate(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in PUBLIC_SCHEMES:
            raise ValueError("only http and https public sources are allowed")
        host = (parsed.hostname or "").lower()
        if not host or host in PRIVATE_HOSTS or host.startswith(PRIVATE_HOST_PREFIXES):
            raise ValueError("private or local network sources are not allowed")
        if host.endswith(".local") or host.endswith(".internal"):
            raise ValueError("internal hostnames are not allowed")


class BrowserResearchAssistant:
    """Tab, note, source, citation, RBAC, and audit workflow for defensive research."""

    ROLE_PERMISSIONS = {
        "analyst": frozenset({"tab.open", "source.capture", "note.write", "summary.write"}),
        "reviewer": frozenset({"audit.read", "summary.approve"}),
        "admin": frozenset({"tab.open", "source.capture", "note.write", "summary.write", "audit.read"}),
    }

    def __init__(self, audit_log: ImmutableAuditLog | None = None) -> None:
        self.audit_log = audit_log or ImmutableAuditLog()
        self.policy = PublicSourcePolicy()
        self.tabs: dict[str, BrowserTab] = {}
        self.sources: dict[str, SourceRecord] = {}
        self.notes: dict[str, ResearchNote] = {}

    def _authorize(self, context: AccessContext, permission: str) -> None:
        allowed = any(permission in self.ROLE_PERMISSIONS.get(role, frozenset()) for role in context.roles)
        self.audit_log.append(
            actor=context.operator_id,
            action="browser.authorize",
            resource=permission,
            decision="ALLOW" if allowed else "DENY",
            payload={"roles": tuple(sorted(context.roles)), "purpose": context.purpose},
        )
        if not allowed:
            raise PermissionError(f"missing permission: {permission}")

    def open_tab(self, context: AccessContext, url: str, title: str) -> BrowserTab:
        self._authorize(context, "tab.open")
        self.policy.validate(url)
        tab = BrowserTab(tab_id=str(uuid4()), url=url, title=title)
        self.tabs[tab.tab_id] = tab
        return tab

    def capture_source(self, context: AccessContext, tab_id: str, content: str, license_hint: str) -> SourceRecord:
        self._authorize(context, "source.capture")
        tab = self.tabs[tab_id]
        record = SourceRecord(
            source_id=str(uuid4()),
            url=tab.url,
            title=tab.title,
            captured_at=datetime.now(UTC),
            content_hash=sha256(content.encode("utf-8")).hexdigest(),
            license_hint=license_hint,
        )
        self.sources[record.source_id] = record
        return record

    def write_note(self, context: AccessContext, tab_id: str, body: str, source_ids: tuple[str, ...]) -> ResearchNote:
        self._authorize(context, "note.write")
        if tab_id not in self.tabs:
            raise ValueError("unknown tab")
        missing = [source_id for source_id in source_ids if source_id not in self.sources]
        if missing:
            raise ValueError(f"unknown source ids: {missing}")
        note = ResearchNote(str(uuid4()), tab_id, body, source_ids, context.operator_id)
        self.notes[note.note_id] = note
        return note

    def summarize(self, context: AccessContext, title: str, claims: tuple[CitedClaim, ...]) -> SummaryArtifact:
        self._authorize(context, "summary.write")
        for claim in claims:
            if not claim.text.strip():
                raise ValueError("claim text is required")
            if not claim.source_ids:
                raise ValueError("every AI summary claim requires at least one citation")
            unknown = [source_id for source_id in claim.source_ids if source_id not in self.sources]
            if unknown:
                raise ValueError(f"claim cites unknown sources: {unknown}")
        return SummaryArtifact(str(uuid4()), title, claims)

    def export_local_snapshot(self) -> str:
        return json.dumps(
            {
                "tabs": [tab.__dict__ | {"opened_at": tab.opened_at.isoformat()} for tab in self.tabs.values()],
                "sources": [
                    source.__dict__ | {"captured_at": source.captured_at.isoformat()}
                    for source in self.sources.values()
                ],
                "notes": [note.__dict__ | {"created_at": note.created_at.isoformat()} for note in self.notes.values()],
            },
            sort_keys=True,
        )
