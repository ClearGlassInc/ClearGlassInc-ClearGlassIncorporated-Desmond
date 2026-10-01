"""Unit tests for the G01 client, telemetry, scanner and gate calculation. No root needed."""

import base64
import json
from pathlib import Path

import pytest

from shield.client.config import ConfigError, ShieldConfig
from shield.client.controller import STATES
from shield.client.telemetry import Telemetry, check
from shield.common import is_wireguard_key
from shield.evidence import CRITERIA, CYCLES, STATIC, evaluate
from shield.secret_scan import scan

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "config.json"


def fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def test_fixture_validates():
    assert ShieldConfig.load(FIXTURE).environment == "isolated-disposable-test"


@pytest.mark.parametrize("changes,error_class", [
    ({"tunnel_address": None}, "missing_field"),
    ({"environment": "staging"}, "non_test_environment"),
    ({"gateway_endpoint": "203.0.113.10:51820"}, "non_test_endpoint"),
    ({"gateway_endpoint": "192.0.2.1:443"}, "non_test_endpoint"),
    ({"tunnel_address": "10.0.0.2/24"}, "non_test_cidr"),
    ({"tunnel_address": "not-an-address"}, "non_test_cidr"),
    ({"public_key": "not-a-wireguard-key"}, "malformed_public_key"),
    ({"public_key": base64.b64encode(b"x" * 31).decode()}, "malformed_public_key"),
    ({"configuration_version": "2"}, "unsupported_version"),
    ({"network_lock": False}, "network_lock_missing"),
    ({"network_lock": "true"}, "network_lock_missing"),
    ({"dns_policy": "198.51.100.53"}, "dns_policy_rejected"),
    ({"debug": True}, "unexpected_field"),
    ({"gateway_identity": ""}, "missing_identity"),
])
def test_invalid_configs_are_rejected(changes, error_class):
    data = fixture()
    for key, value in changes.items():
        if value is None:
            data.pop(key)
        else:
            data[key] = value
    with pytest.raises(ConfigError) as exc:
        ShieldConfig.from_dict(data)
    assert exc.value.error_class == error_class


def test_key_shape():
    assert is_wireguard_key(fixture()["public_key"])
    assert not is_wireguard_key("A" * 44)
    assert not is_wireguard_key(base64.b64encode(b"x" * 33).decode())


def test_controller_has_every_required_state():
    required = {"INITIALIZED", "CONFIG_VALIDATING", "CONFIG_VALID", "AUTHENTICATING", "CONNECTING",
                "HANDSHAKING", "CONNECTED", "HEALTHY", "DISCONNECTING", "DISCONNECTED",
                "CONFIG_FAILURE", "AUTH_FAILURE", "GATEWAY_UNAVAILABLE", "HANDSHAKE_FAILURE",
                "TUNNEL_FAILURE", "DNS_FAILURE", "REVOKED", "NETWORK_LOCK_ACTIVE"}
    assert required <= set(STATES)


def test_telemetry_refuses_fields_outside_allowlist(tmp_path):
    t = Telemetry(tmp_path / "t.jsonl", run_id="r", test_id="x")
    event = t.emit(component="client", state="HEALTHY")
    assert event["telemetry_scope"] == "TEST_ONLY"
    assert event["production_equivalence"] == "NOT_ESTABLISHED"
    with pytest.raises(ValueError):
        t.emit(component="client", client_ip="10.77.0.2")
    with pytest.raises(ValueError):
        check({"state": "x" * 200})
    assert len((tmp_path / "t.jsonl").read_text().splitlines()) == 1


def test_scanner_finds_planted_material(tmp_path):
    key = base64.b64encode(bytes(range(32))).decode()
    (tmp_path / "a.conf").write_text("".join(("[Interface]\nPrivate", "Key = ", key, "\n")))
    (tmp_path / "b.json").write_text(json.dumps({"private_key": key}))
    (tmp_path / "c.txt").write_text("".join(("-----BEGIN ", "PRIVATE KEY-----\n")))
    (tmp_path / "d.txt").write_text("".join(("token sk_", "live_", "abcdefghijkl\n")))
    (tmp_path / "e.key").write_text("x")
    rules = {f["rule"] for f in scan([tmp_path])}
    assert rules == {"wireguard-private-key-line", "private-key-field", "pem-private-key",
                     "stripe-live-secret", "forbidden-file-type"}


def test_scanner_passes_clean_text_and_public_keys(tmp_path):
    (tmp_path / "ok.json").write_text(json.dumps({"public_key": fixture()["public_key"]}))
    assert scan([tmp_path]) == []


def _records(status: str = "PASS") -> dict:
    runtime = {t for _, tests in CRITERIA for t in tests} - STATIC
    rec = {"static": {t: {"status": "PASS"} for t in STATIC}}
    for cycle in CYCLES:
        rec[cycle] = {t: {"status": status} for t in runtime}
    return rec


def test_gate_passes_only_when_everything_passes():
    assert evaluate(_records(), True, True)["gate_decision"] == "PASS"


@pytest.mark.parametrize("mutate", [
    lambda r: r["cycle-2"]["FI-03"].update(status="FAIL"),
    lambda r: r["cycle-1"]["LOCK-02"].update(status="SKIPPED"),
    lambda r: r["cycle-2"].pop("FI-14"),
    lambda r: r.pop("cycle-2"),
    lambda r: r["static"]["TREE-01"].update(status="FAIL"),
])
def test_gate_fails_on_any_failed_skipped_or_missing_test(mutate):
    records = _records()
    mutate(records)
    assert evaluate(records, True, True)["gate_decision"] == "FAIL"


def test_gate_fails_on_boundary_conditions():
    assert evaluate(_records(), False, True)["gate_decision"] == "FAIL"
    assert evaluate(_records(), True, False)["gate_decision"] == "FAIL"
    assert evaluate(_records(), True, True, stripe_interactions=1)["gate_decision"] == "FAIL"
    assert evaluate(_records(), True, True, production_interactions=1)["gate_decision"] == "FAIL"
    assert evaluate(_records(), True, True, customer_traffic=True)["gate_decision"] == "FAIL"
