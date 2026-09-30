from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
FORBIDDEN_FILES={".env","client.key","gateway.key","client-private.key","gateway-private.key"}
# Assembled at runtime so this file, which is inside shield/, does not contain
# the markers it scans shield/ for. Written as literals, the test (and the
# workflow's "Verify repository boundary" grep) flagged this line on every run.
PRODUCTION_MARKERS=tuple("".join(p) for p in (("sk_","live_"),("STRIPE_","SECRET"),("production_","endpoint"),("customer_traffic_","endpoint")))

def test_no_private_material_in_repo():
    names={p.name for p in REPO.rglob("*") if p.is_file()}
    assert not FORBIDDEN_FILES.intersection(names)

def test_shield_source_contains_no_live_secret_markers():
    for p in (REPO/"shield").rglob("*"):
        if not p.is_file():
            continue
        text=p.read_text(encoding="utf-8",errors="ignore")
        assert not any(marker in text for marker in PRODUCTION_MARKERS), p
