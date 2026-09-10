"""Tests for products/opal-koboi/opal_security.py.

Stdlib + pytest only, so they run in CI without the product's heavy
dependencies. The encryption round-trip uses `importorskip` so it is exercised
when `cryptography` is installed and cleanly skipped when it is not.
"""
import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# opal_security lives in a hyphenated directory (not an importable package name),
# so load it by file path. Register it in sys.modules before exec so dataclasses
# can resolve the module — but avoid mutating sys.path for other tests.
_OPAL_FILE = Path(__file__).resolve().parents[1] / "products" / "opal-koboi" / "opal_security.py"
_spec = importlib.util.spec_from_file_location("opal_security", _OPAL_FILE)
sec = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = sec
_spec.loader.exec_module(sec)


def _require_crypto():
    """Skip (not fail) when the cryptography native backend is unavailable.

    pytest.importorskip only catches ImportError, but a broken/missing native
    binding (e.g. absent _cffi_backend) surfaces as pyo3_runtime.PanicException,
    which is NOT an ImportError — so it would fail the suite red on an
    environment that simply lacks the compiled dependency. The EncryptedVault
    code is unchanged; this only keeps the harness honest across environments.
    """
    try:
        import cryptography.fernet  # noqa: F401
    except BaseException as exc:  # noqa: BLE001 — import probe; any failure → skip
        pytest.skip(f"cryptography native backend unavailable: {exc!r}")


# --------------------------------------------------------------------------- #
# AuditLedger
# --------------------------------------------------------------------------- #
def test_audit_ledger_chains_and_verifies():
    ledger = sec.AuditLedger()
    e1 = ledger.append("enroll", subject="alice")
    e2 = ledger.append("identify", subject="alice", confidence=0.97)
    assert e1["prev_hash"] == sec.AuditLedger.GENESIS
    assert e2["prev_hash"] == e1["entry_hash"]
    assert ledger.verify() is True


def test_audit_ledger_detects_tampering():
    ledger = sec.AuditLedger()
    ledger.append("enroll", subject="alice")
    ledger.append("identify", subject="bob")
    # Mutate a recorded field without recomputing the hash -> chain breaks.
    ledger._entries[0]["data"]["subject"] = "mallory"
    assert ledger.verify() is False


def test_audit_ledger_persists_and_reloads(tmp_path):
    path = tmp_path / "ledger.json"
    led = sec.AuditLedger(path)
    led.append("enroll", subject="alice")
    led.append("delete", subject="alice")
    reloaded = sec.AuditLedger(path)
    assert len(reloaded.entries) == 2
    assert reloaded.verify() is True


# --------------------------------------------------------------------------- #
# RetentionPolicy
# --------------------------------------------------------------------------- #
def test_retention_expiry_boundary():
    pol = sec.RetentionPolicy(ttl_days=30)
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    old = (now - timedelta(days=31)).isoformat()
    fresh = (now - timedelta(days=29)).isoformat()
    assert pol.is_expired(old, now=now) is True
    assert pol.is_expired(fresh, now=now) is False


def test_retention_disabled_when_ttl_non_positive():
    pol = sec.RetentionPolicy(ttl_days=0)
    ancient = datetime(1990, 1, 1, tzinfo=timezone.utc).isoformat()
    assert pol.is_expired(ancient) is False


def test_retention_partition():
    pol = sec.RetentionPolicy(ttl_days=10)
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    records = [
        {"name": "old", "enrollment_date": (now - timedelta(days=40)).isoformat()},
        {"name": "new", "enrollment_date": (now - timedelta(days=1)).isoformat()},
        {"name": "bad", "enrollment_date": "not-a-date"},
    ]
    kept, expired = pol.partition(records, now=now)
    assert {r["name"] for r in kept} == {"new", "bad"}  # unparseable is retained
    assert [r["name"] for r in expired] == ["old"]


# --------------------------------------------------------------------------- #
# ConsentRegistry
# --------------------------------------------------------------------------- #
def test_consent_required_before_grant():
    reg = sec.ConsentRegistry()
    with pytest.raises(sec.ConsentError):
        reg.require("alice")
    reg.record("alice")
    reg.require("alice")  # no longer raises
    assert reg.has_consent("alice") is True


def test_consent_revoke():
    reg = sec.ConsentRegistry()
    reg.record("alice")
    assert reg.revoke("alice") is True
    assert reg.revoke("alice") is False
    with pytest.raises(sec.ConsentError):
        reg.require("alice")


def test_consent_state_rebuilt_from_ledger():
    ledger = sec.AuditLedger()
    sec.ConsentRegistry(ledger=ledger).record("alice")
    # A fresh registry over the same ledger must see the prior grant.
    rebuilt = sec.ConsentRegistry(ledger=ledger)
    assert rebuilt.has_consent("alice") is True
    assert ledger.verify() is True


# --------------------------------------------------------------------------- #
# LivenessPolicy
# --------------------------------------------------------------------------- #
def test_liveness_required_fails_closed_without_score():
    passed, reason = sec.LivenessPolicy(required=True).evaluate(None)
    assert passed is False and "required" in reason


def test_liveness_optional_passes_without_score():
    passed, _ = sec.LivenessPolicy(required=False).evaluate(None)
    assert passed is True


def test_liveness_threshold():
    pol = sec.LivenessPolicy(threshold=0.6)
    assert pol.evaluate(0.7)[0] is True
    assert pol.evaluate(0.5)[0] is False
    assert pol.evaluate(1.5)[0] is False  # out of range


# --------------------------------------------------------------------------- #
# EncryptedVault (round-trip requires the cryptography lib)
# --------------------------------------------------------------------------- #
def test_vault_envelope_constant():
    assert sec._VAULT_MAGIC == b"OPALVAULT1"


def test_vault_roundtrip_and_tamper(tmp_path):
    _require_crypto()
    vault = sec.EncryptedVault(tmp_path / "vault.key")
    assert vault.crypto_available() is True
    obj = {"encodings": [[0.1, 0.2, 0.3]], "names": ["alice"], "metadata": [{}]}
    data_path = tmp_path / "db.enc"
    vault.save(data_path, obj)
    blob = data_path.read_bytes()
    assert b"alice" not in blob  # encrypted at rest, not plaintext
    assert vault.load(data_path) == obj
    # Tampered ciphertext must fail closed.
    data_path.write_bytes(blob[:-2] + b"xy")
    with pytest.raises(ValueError):
        vault.load(data_path)


def test_vault_key_file_permissions(tmp_path):
    _require_crypto()
    key_path = tmp_path / "vault.key"
    sec.EncryptedVault(key_path)
    assert key_path.exists()
    if hasattr(__import__("os"), "getuid"):  # POSIX only
        assert (key_path.stat().st_mode & 0o077) == 0  # no group/other access
