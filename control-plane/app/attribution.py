"""Campaign attribution carried from checkout to the paid order.

The same three UTM values travel the whole path: the checkout request or the
CRCS lead, then Stripe Checkout metadata, then the verified webhook, then the
order row the revenue cockpit groups by. Stripe echoes metadata back unchanged,
so this is the only way a paid order can say which campaign produced it.

Attribution is marketing context, never a reason to refuse a purchase: a value
that fails validation is dropped, not rejected. Values are restricted to the
characters campaign tags use (``CG-LINKEDIN-AI-GOVERNANCE-2026``), so free text
or personal data cannot ride along into Stripe or the ledger.

Stdlib only, like ``governance.py``.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

KEYS = ("utm_source", "utm_medium", "utm_campaign")

#: Stripe metadata keys, prefixed so they cannot collide with the ``skus`` /
#: ``crcs_*`` keys ``payments.create_checkout_session`` already writes.
METADATA_PREFIX = "cg_"

_VALUE = re.compile(r"^[A-Za-z0-9._\-]{1,120}$")


def clean(raw: Mapping[str, Any] | None) -> dict[str, str]:
    """Keep only known keys whose values look like campaign tags."""
    if not raw:
        return {}
    cleaned: dict[str, str] = {}
    for key in KEYS:
        value = raw.get(key)
        if isinstance(value, str) and _VALUE.match(value.strip()):
            cleaned[key] = value.strip()
    return cleaned


def to_metadata(raw: Mapping[str, Any] | None) -> dict[str, str]:
    """Attribution as Stripe Checkout metadata."""
    return {f"{METADATA_PREFIX}{key}": value for key, value in clean(raw).items()}


def from_metadata(metadata: Mapping[str, Any] | None) -> dict[str, str]:
    """Read attribution back off a Stripe object, re-validating it.

    Payment Links and anything created outside this code carry no ``cg_`` keys,
    which yields ``{}``: an unattributed order, never a guessed one.
    """
    if not metadata:
        return {}
    return clean({key: metadata.get(f"{METADATA_PREFIX}{key}") for key in KEYS})
