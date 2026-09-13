from __future__ import annotations

from app.routers.subscriptions import ACTIVE_STATUSES, _price_plan


def test_active_subscription_statuses_are_entitled() -> None:
    assert "active" in ACTIVE_STATUSES
    assert "trialing" in ACTIVE_STATUSES
    assert "canceled" not in ACTIVE_STATUSES
    assert "unpaid" not in ACTIVE_STATUSES


def test_price_id_maps_to_server_owned_subscription_sku() -> None:
    assert _price_plan("price_1U0wlFL8uR92FksUG6ZT87rG") == "business-protection-monthly"
    assert _price_plan("price_1U0wlOL8uR92FksUJjFEMvGT") == "business-protection-annual"
    assert _price_plan("price_not_in_pricebook") == "unknown"
