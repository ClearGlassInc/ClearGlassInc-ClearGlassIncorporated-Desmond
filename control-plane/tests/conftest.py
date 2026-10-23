"""Make the control-plane package importable when running tests locally."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE))


@pytest.fixture()
def crcs_offer_on_sale(monkeypatch, tmp_path):
    """A copy of the price book with the CRCS first offer marked for sale.

    The owner took `rapid-website-deployment-diagnostic` off sale on 2026-10-15
    (it has no Stripe Price yet). Tests that exercise the CRCS checkout path's
    gating and privacy rules still need an offer to gate, so they get one here,
    from a temporary file — never by editing the committed price book, whose
    `active` flag is the owner's decision.
    """
    from app import config as config_module
    from app import pricebook

    sku = config_module.get_settings().crcs_first_offer_sku
    document = json.loads(pricebook.DEFAULT_PRICEBOOK.read_text(encoding="utf-8"))
    for offer in document["offers"]:
        if offer["sku"] == sku:
            offer["active"] = True
    on_sale = tmp_path / "pricebook.json"
    on_sale.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setenv("PRICEBOOK_PATH", str(on_sale))
    pricebook.reload()
    yield sku
    monkeypatch.delenv("PRICEBOOK_PATH", raising=False)
    pricebook.reload()
