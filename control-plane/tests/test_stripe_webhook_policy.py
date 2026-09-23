"""Regression tests for Stripe webhook signature enforcement policy."""
from __future__ import annotations

from app import payments


def test_production_requires_stripe_webhook_signature(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    assert payments.webhook_requires_signature() is True


def test_test_key_requires_stripe_webhook_signature(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_not_a_credential")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    assert payments.webhook_requires_signature() is True


def test_local_mock_mode_preserves_unconfigured_webhook_behavior(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    assert payments.webhook_requires_signature() is False
