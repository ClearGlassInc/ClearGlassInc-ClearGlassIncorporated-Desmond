"""opal_security.py — privacy & integrity primitives for Opal-Koboi.

Dependency-light hardening for the facial-recognition system, along the axes
enterprises actually require: explicit consent, encryption-at-rest, retention
limits, and a tamper-evident audit trail. None of these add any surveillance or
mass-identification capability — they only make the *consent-based* product
safer and more compliant (GDPR / CCPA / BIPA).

Design notes:
* Pure Python stdlib at import time. `EncryptedVault` imports `cryptography`
  lazily, so the rest of the module (and its tests) run without it installed.
* Every primitive here is unit-tested in tests/test_opal_security.py.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _canonical(obj: Any) -> bytes:
    """Stable JSON encoding for hashing (sorted keys, no incidental whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


# --------------------------------------------------------------------------- #
# Tamper-evident audit ledger
# --------------------------------------------------------------------------- #
@dataclass
class AuditLedger:
    """Append-only, hash-chained audit log (sha256).

    Each entry embeds the hash of the previous entry, so any retroactive edit or
    deletion breaks the chain and `verify()` returns False. Same tamper-evidence
    model as the autostore control plane.
    """

    path: Optional[Path] = None
    _entries: list[dict] = field(default_factory=list)

    GENESIS = "0" * 64

    def __post_init__(self) -> None:
        if self.path is not None:
            self.path = Path(self.path)
            if self.path.exists():
                self._entries = json.loads(self.path.read_text(encoding="utf-8"))

    @property
    def entries(self) -> list[dict]:
        return list(self._entries)

    def _prev_hash(self) -> str:
        return self._entries[-1]["entry_hash"] if self._entries else self.GENESIS

    @staticmethod
    def _hash_entry(entry: dict) -> str:
        material = {k: entry[k] for k in ("id", "ts", "action", "data", "prev_hash")}
        return hashlib.sha256(_canonical(material)).hexdigest()

    def append(self, action: str, **fields: Any) -> dict:
        """Append an event and persist (if backed by a file). Returns the entry."""
        entry = {
            "id": len(self._entries) + 1,
            "ts": _utcnow().isoformat(),
            "action": action,
            "data": fields,
            "prev_hash": self._prev_hash(),
        }
        entry["entry_hash"] = self._hash_entry(entry)
        self._entries.append(entry)
        self._flush()
        return entry

    def verify(self) -> bool:
        """True iff the whole chain is internally consistent (untampered)."""
        prev = self.GENESIS
        for entry in self._entries:
            if entry.get("prev_hash") != prev:
                return False
            if entry.get("entry_hash") != self._hash_entry(entry):
                return False
            prev = entry["entry_hash"]
        return True

    def _flush(self) -> None:
        if self.path is not None:
            self.path.write_text(json.dumps(self._entries, indent=2, default=str), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Retention / data-minimization
# --------------------------------------------------------------------------- #
@dataclass
class RetentionPolicy:
    """Time-boxed retention for biometric records (BIPA/GDPR data-minimization).

    A record is expired when its enrollment timestamp is older than `ttl_days`.
    `ttl_days <= 0` disables expiry (retain indefinitely — an explicit choice).
    """

    ttl_days: int

    def is_expired(self, ts_iso: str, now: Optional[datetime] = None) -> bool:
        if self.ttl_days <= 0:
            return False
        now = now or _utcnow()
        try:
            ts = datetime.fromisoformat(ts_iso)
        except (TypeError, ValueError):
            return False  # unparseable timestamps are never auto-purged
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (now - ts) > timedelta(days=self.ttl_days)

    def partition(
        self,
        records: Iterable[dict],
        key: str = "enrollment_date",
        now: Optional[datetime] = None,
    ) -> tuple[list[dict], list[dict]]:
        """Split records into (kept, expired) by their `key` timestamp."""
        kept: list[dict] = []
        expired: list[dict] = []
        for rec in records:
            (expired if self.is_expired(rec.get(key, ""), now) else kept).append(rec)
        return kept, expired


# --------------------------------------------------------------------------- #
# Consent
# --------------------------------------------------------------------------- #
class ConsentError(RuntimeError):
    """Raised when an operation requires consent that has not been recorded."""


@dataclass
class ConsentRegistry:
    """Records and enforces explicit, per-subject consent.

    Consent grants/revocations are written to the tamper-evident `ledger`, and
    current state is rebuilt from it on construction. `require()` raises
    `ConsentError` when consent is absent, so the enrollment path cannot
    silently skip it.
    """

    ledger: Optional[AuditLedger] = None
    _granted: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.ledger is not None:
            for e in self.ledger.entries:
                if e.get("action") == "consent_granted":
                    self._granted[e["data"]["subject"]] = e["data"]
                elif e.get("action") == "consent_revoked":
                    self._granted.pop(e["data"].get("subject"), None)

    def record(
        self,
        subject: str,
        purpose: str = "facial recognition enrollment",
        method: str = "explicit",
    ) -> dict:
        rec = {"subject": subject, "purpose": purpose, "method": method, "ts": _utcnow().isoformat()}
        self._granted[subject] = rec
        if self.ledger is not None:
            self.ledger.append("consent_granted", **rec)
        return rec

    def has_consent(self, subject: str) -> bool:
        return subject in self._granted

    def require(self, subject: str) -> None:
        if not self.has_consent(subject):
            raise ConsentError(f"no recorded consent for {subject!r}; operation refused")

    def revoke(self, subject: str) -> bool:
        existed = self._granted.pop(subject, None) is not None
        if existed and self.ledger is not None:
            self.ledger.append("consent_revoked", subject=subject)
        return existed


# --------------------------------------------------------------------------- #
# Encryption-at-rest
# --------------------------------------------------------------------------- #
_VAULT_MAGIC = b"OPALVAULT1"  # envelope version tag


class EncryptedVault:
    """Encryption-at-rest for the biometric template store.

    Backed by `cryptography.Fernet` (AES-128-CBC + HMAC-SHA256). The key lives
    in its own file with 0600 permissions; templates are never written in
    plaintext, and decryption fails closed on any tampering or wrong key.
    """

    def __init__(self, key_path: str | os.PathLike):
        self.key_path = Path(key_path)
        self._fernet = self._load_or_create_key()

    @staticmethod
    def crypto_available() -> bool:
        try:
            import cryptography.fernet  # noqa: F401
        except Exception:
            return False
        return True

    def _load_or_create_key(self):
        try:
            from cryptography.fernet import Fernet
        except Exception as exc:  # pragma: no cover - exercised only without the lib
            raise RuntimeError(
                "EncryptedVault requires the 'cryptography' package (pip install cryptography)"
            ) from exc
        if self.key_path.exists():
            key = self.key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)
            try:
                os.chmod(self.key_path, 0o600)
            except OSError:  # pragma: no cover - non-POSIX filesystems
                pass
        return Fernet(key)

    def encrypt(self, obj: Any) -> bytes:
        payload = _VAULT_MAGIC + json.dumps(obj, default=str).encode("utf-8")
        return self._fernet.encrypt(payload)

    def decrypt(self, token: bytes) -> Any:
        from cryptography.fernet import InvalidToken

        try:
            payload = self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise ValueError("vault payload failed integrity check (tampered or wrong key)") from exc
        if not payload.startswith(_VAULT_MAGIC):
            raise ValueError("unrecognized vault envelope")
        return json.loads(payload[len(_VAULT_MAGIC):].decode("utf-8"))

    def save(self, data_path: str | os.PathLike, obj: Any) -> None:
        Path(data_path).write_bytes(self.encrypt(obj))

    def load(self, data_path: str | os.PathLike) -> Any:
        p = Path(data_path)
        if not p.exists():
            return None
        return self.decrypt(p.read_bytes())


# --------------------------------------------------------------------------- #
# Liveness / anti-spoofing gate
# --------------------------------------------------------------------------- #
@dataclass
class LivenessPolicy:
    """Anti-spoofing gate for the authentication path.

    Liveness *scoring* (blink / texture / depth analysis) is supplied by the
    caller as a score in [0, 1]; this policy decides pass/fail. With
    `required=True`, a missing score fails closed — defeating photo-replay
    attacks without pulling heavy CV dependencies into this module.
    """

    threshold: float = 0.5
    required: bool = False

    def evaluate(self, score: Optional[float]) -> tuple[bool, str]:
        if score is None:
            if self.required:
                return False, "liveness required but no score provided"
            return True, "liveness not enforced"
        if not 0.0 <= score <= 1.0:
            return False, f"invalid liveness score {score!r}"
        if score >= self.threshold:
            return True, f"liveness ok ({score:.2f} >= {self.threshold:.2f})"
        return False, f"liveness failed ({score:.2f} < {self.threshold:.2f})"
