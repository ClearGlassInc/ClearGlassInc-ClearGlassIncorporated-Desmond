from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
FORBIDDEN_FILES={".env","client.key","gateway.key","client-private.key","gateway-private.key"}
PRODUCTION_MARKERS=("sk_live_","STRIPE_SECRET","production_endpoint","customer_traffic_endpoint")

def test_no_private_material_in_repo():
    names={p.name for p in REPO.rglob("*") if p.is_file()}
    assert not FORBIDDEN_FILES.intersection(names)

def test_shield_source_contains_no_live_secret_markers():
    for p in (REPO/"shield").rglob("*"):
        if not p.is_file(): continue
        text=p.read_text(encoding="utf-8",errors="ignore")
        assert not any(marker in text for marker in PRODUCTION_MARKERS), p
