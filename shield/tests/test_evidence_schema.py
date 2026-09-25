import json
from pathlib import Path

def test_fixture_is_valid_json():
    p=Path(__file__).resolve().parents[1]/"fixtures"/"config.json"
    d=json.loads(p.read_text())
    assert d["environment"]=="isolated-disposable-test"
    assert d["network_lock"] is True
    assert d["dns_policy"]=="test-only"
