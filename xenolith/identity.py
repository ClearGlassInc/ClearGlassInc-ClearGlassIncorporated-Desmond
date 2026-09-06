# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH identity layer — cryptographic, sponsor-owned agent identity.

Nothing in the lattice acts anonymously. Every agent is issued a credential
derived from a lattice root secret, and every consequential action travels as a
signed :class:`Envelope` that names its author, carries a nonce, and expires.

Three properties the rest of the platform depends on:

* **Derived, never stored keys.** Agent keys are HMAC-derived from the root
  secret on demand, so no per-agent key material is written to disk or to a
  repository. The root secret is generated at runtime unless one is injected.
* **Replay protection.** A verified nonce is burned. Re-presenting a valid
  envelope fails, which is what makes the audit ledger's ordering meaningful.
* **Revocation is immediate and fail-closed.** A revoked codename cannot sign
  and its outstanding envelopes stop verifying.

Stdlib only (``hmac``, ``hashlib``, ``secrets``), to match the other governed
ClearGlass modules.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from .constants import IdentityError, canonical

#: Envelopes older than this are rejected regardless of signature validity.
DEFAULT_ENVELOPE_TTL_SECONDS = 300

_KEY_INFO = b"xenolith/agent-key/v1"


@dataclass(frozen=True)
class Credential:
    """A non-secret handle to an issued identity.

    Holds no key material — only the fingerprint, which is safe to log, embed
    in dashboards, and compare. The key itself is re-derived on demand from the
    authority's root secret.
    """

    codename: str
    sponsor: str
    key_id: str
    fingerprint: str
    issued_at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "codename": self.codename,
            "sponsor": self.sponsor,
            "key_id": self.key_id,
            "fingerprint": self.fingerprint,
            "issued_at": self.issued_at,
        }


@dataclass(frozen=True)
class Envelope:
    """A signed statement of intent from a named agent.

    ``payload`` is the action being claimed; the signature covers the payload
    *and* the codename, nonce and timestamp together, so none of them can be
    swapped without invalidating the envelope.
    """

    codename: str
    payload: Mapping[str, Any]
    nonce: str
    issued_at: float
    signature: str

    def signed_body(self) -> dict[str, Any]:
        """The exact structure the signature is computed over."""
        return {
            "codename": self.codename,
            "payload": dict(self.payload),
            "nonce": self.nonce,
            "issued_at": self.issued_at,
        }

    def as_dict(self) -> dict[str, Any]:
        body = self.signed_body()
        body["signature"] = self.signature
        return body


class IdentityAuthority:
    """Issues, signs for, verifies and revokes lattice identities.

    Parameters
    ----------
    root_secret:
        Optional injected root secret. When omitted a cryptographically random
        one is generated for the process — the safe default, and the reason no
        secret needs to live in the repository. Inject one only when identities
        must survive a restart, and source it from the environment.
    envelope_ttl:
        Seconds an envelope stays valid after issuance.
    """

    def __init__(
        self,
        root_secret: bytes | None = None,
        envelope_ttl: int = DEFAULT_ENVELOPE_TTL_SECONDS,
    ) -> None:
        if envelope_ttl <= 0:
            raise ValueError("envelope_ttl must be positive")
        self._root = root_secret or secrets.token_bytes(32)
        self._ttl = envelope_ttl
        self._credentials: dict[str, Credential] = {}
        self._revoked: set[str] = set()
        self._seen_nonces: dict[str, float] = {}

    # ------------------------------------------------------------------ #
    # Issuance
    # ------------------------------------------------------------------ #
    def issue(self, codename: str, sponsor: str) -> Credential:
        """Issue a credential for ``codename``, accountable to ``sponsor``.

        An unsponsored identity is not permitted: every autonomous actor traces
        back to a named human.
        """
        codename = _require(codename, "codename")
        sponsor = _require(sponsor, "sponsor")
        if codename in self._credentials:
            raise IdentityError(f"identity already issued: {codename}")
        if codename in self._revoked:
            raise IdentityError(f"codename is revoked and cannot be reissued: {codename}")

        key = self._derive_key(codename)
        fingerprint = hashlib.sha256(key).hexdigest()[:32]
        credential = Credential(
            codename=codename,
            sponsor=sponsor,
            key_id=f"xk-{fingerprint[:12]}",
            fingerprint=fingerprint,
            issued_at=time.time(),
        )
        self._credentials[codename] = credential
        return credential

    def revoke(self, codename: str) -> None:
        """Revoke an identity. Idempotent; unknown codenames are still burned."""
        self._credentials.pop(codename, None)
        self._revoked.add(codename)

    def is_active(self, codename: str) -> bool:
        return codename in self._credentials and codename not in self._revoked

    def credential(self, codename: str) -> Credential:
        try:
            return self._credentials[codename]
        except KeyError:
            raise IdentityError(f"unknown identity: {codename}") from None

    @property
    def codenames(self) -> tuple[str, ...]:
        return tuple(sorted(self._credentials))

    # ------------------------------------------------------------------ #
    # Signing & verification
    # ------------------------------------------------------------------ #
    def sign(self, codename: str, payload: Mapping[str, Any]) -> Envelope:
        """Produce a signed, single-use envelope for ``payload``."""
        if not self.is_active(codename):
            raise IdentityError(f"cannot sign for inactive or unknown identity: {codename}")
        nonce = secrets.token_hex(16)
        issued_at = time.time()
        body = {
            "codename": codename,
            "payload": dict(payload),
            "nonce": nonce,
            "issued_at": issued_at,
        }
        return Envelope(
            codename=codename,
            payload=dict(payload),
            nonce=nonce,
            issued_at=issued_at,
            signature=self._mac(codename, body),
        )

    def verify(self, envelope: Envelope, *, burn: bool = True) -> bool:
        """Verify signature, expiry, revocation and replay in one pass.

        Returns ``True`` only if every check passes. Set ``burn=False`` to
        inspect an envelope without consuming its nonce — useful for dry-run
        policy evaluation, where the same envelope is checked before it is
        actually executed.
        """
        if not self.is_active(envelope.codename):
            return False
        if time.time() - envelope.issued_at > self._ttl:
            return False
        if envelope.issued_at > time.time() + self._ttl:
            # Clock-skew or forged future timestamp; refuse rather than trust.
            return False

        expected = self._mac(envelope.codename, envelope.signed_body())
        if not hmac.compare_digest(expected, envelope.signature):
            return False

        self._expire_nonces()
        if envelope.nonce in self._seen_nonces:
            return False
        if burn:
            self._seen_nonces[envelope.nonce] = envelope.issued_at
        return True

    def require(self, envelope: Envelope) -> Envelope:
        """Verify or raise. Use where a failed check must stop the flow."""
        if not self.verify(envelope):
            raise IdentityError(
                f"envelope rejected for {envelope.codename} "
                "(bad signature, expired, replayed, or revoked)"
            )
        return envelope

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _derive_key(self, codename: str) -> bytes:
        return hmac.new(self._root, _KEY_INFO + codename.encode("utf-8"), hashlib.sha256).digest()

    def _mac(self, codename: str, body: Mapping[str, Any]) -> str:
        return hmac.new(self._derive_key(codename), canonical(body), hashlib.sha256).hexdigest()

    def _expire_nonces(self) -> None:
        """Drop nonces that can no longer be replayed, bounding memory growth."""
        cutoff = time.time() - self._ttl
        stale = [nonce for nonce, issued in self._seen_nonces.items() if issued < cutoff]
        for nonce in stale:
            del self._seen_nonces[nonce]


@dataclass
class IdentitySnapshot:
    """Operator-facing view of the identity layer."""

    active: int
    revoked: int
    credentials: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"active": self.active, "revoked": self.revoked, "credentials": self.credentials}


def snapshot(authority: IdentityAuthority) -> IdentitySnapshot:
    """Build a redacted, dashboard-safe view — fingerprints only, no keys."""
    creds = [authority.credential(name).as_dict() for name in authority.codenames]
    return IdentitySnapshot(
        active=len(creds),
        revoked=len(authority._revoked),  # noqa: SLF001 - same-module accessor
        credentials=creds,
    )


def _require(value: str, label: str) -> str:
    if not value or not value.strip():
        raise IdentityError(f"{label} is required")
    return value.strip()
