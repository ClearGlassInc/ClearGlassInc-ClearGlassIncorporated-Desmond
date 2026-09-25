from __future__ import annotations
from dataclasses import dataclass
import hashlib, ipaddress, json, re
from pathlib import Path

TEST_ENV="isolated-disposable-test"
TEST_GATEWAY_RE=re.compile(r"^192\.0\.2\.(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]):51820$")

@dataclass(frozen=True)
class ShieldConfig:
    environment: str
    gateway_endpoint: str
    gateway_identity: str
    public_key: str
    tunnel_address: str
    dns_policy: str
    network_lock: bool
    configuration_version: str

    @classmethod
    def load(cls, path: Path) -> "ShieldConfig":
        data=json.loads(path.read_text(encoding="utf-8"))
        required={"environment","gateway_endpoint","gateway_identity","public_key","tunnel_address","dns_policy","network_lock","configuration_version"}
        missing=required-data.keys()
        if missing:
            raise ValueError("missing configuration fields: "+str(sorted(missing)))
        if set(data) != required:
            raise ValueError("unexpected configuration fields")
        if data["environment"] != TEST_ENV:
            raise ValueError("refusing non-test environment")
        if not TEST_GATEWAY_RE.fullmatch(data["gateway_endpoint"]):
            raise ValueError("gateway endpoint is outside reserved test range")
        if data["dns_policy"] != "test-only":
            raise ValueError("refusing non-test DNS policy")
        if data["network_lock"] is not True:
            raise ValueError("test configuration must enable network lock")
        if data["configuration_version"] != "1":
            raise ValueError("unsupported configuration version")
        network=ipaddress.ip_interface(data["tunnel_address"])
        if network.network != ipaddress.ip_network("10.77.0.0/24"):
            raise ValueError("tunnel address is outside test network")
        if not data["gateway_identity"] or not data["public_key"]:
            raise ValueError("identity fields must not be empty")
        return cls(**{k:data[k] for k in required})

    def fingerprint(self)->str:
        canonical=json.dumps(self.__dict__,sort_keys=True,separators=(",",":")).encode()
        return hashlib.sha256(canonical).hexdigest()
