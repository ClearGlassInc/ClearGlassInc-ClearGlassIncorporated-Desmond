from __future__ import annotations
from dataclasses import dataclass
import hashlib
import ipaddress
import json
import re
from pathlib import Path

from shield.common import is_wireguard_key

TEST_ENV="isolated-disposable-test"
TEST_GATEWAY_RE=re.compile(r"^192\.0\.2\.(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]):51820$")
REQUIRED=frozenset({"environment","gateway_endpoint","gateway_identity","public_key","tunnel_address","dns_policy","network_lock","configuration_version"})


class ConfigError(ValueError):
    """A rejected configuration. error_class is a stable, non-sensitive telemetry value."""

    def __init__(self, error_class: str, message: str):
        super().__init__(message)
        self.error_class=error_class


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
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError("config_unreadable","configuration is not readable JSON") from exc
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: object) -> "ShieldConfig":
        if not isinstance(data,dict):
            raise ConfigError("config_not_object","configuration must be a JSON object")
        missing=REQUIRED-data.keys()
        if missing:
            raise ConfigError("missing_field","missing configuration fields: "+str(sorted(missing)))
        if set(data) != REQUIRED:
            raise ConfigError("unexpected_field","unexpected configuration fields")
        if data["configuration_version"] != "1":
            raise ConfigError("unsupported_version","unsupported configuration version")
        if data["environment"] != TEST_ENV:
            raise ConfigError("non_test_environment","refusing non-test environment")
        if not isinstance(data["gateway_endpoint"],str) or not TEST_GATEWAY_RE.fullmatch(data["gateway_endpoint"]):
            raise ConfigError("non_test_endpoint","gateway endpoint is outside reserved test range")
        if data["dns_policy"] != "test-only":
            raise ConfigError("dns_policy_rejected","refusing non-test DNS policy")
        if data["network_lock"] is not True:
            raise ConfigError("network_lock_missing","test configuration must enable network lock")
        try:
            network=ipaddress.ip_interface(data["tunnel_address"])
        except (TypeError, ValueError) as exc:
            raise ConfigError("non_test_cidr","tunnel address is not an interface address") from exc
        if network.network != ipaddress.ip_network("10.77.0.0/24"):
            raise ConfigError("non_test_cidr","tunnel address is outside test network")
        if not isinstance(data["gateway_identity"],str) or not data["gateway_identity"]:
            raise ConfigError("missing_identity","gateway identity must not be empty")
        if not isinstance(data["public_key"],str) or not is_wireguard_key(data["public_key"]):
            raise ConfigError("malformed_public_key","gateway public key is not a WireGuard key")
        return cls(**{k:data[k] for k in REQUIRED})

    @property
    def gateway_host(self) -> str:
        return self.gateway_endpoint.rsplit(":",1)[0]

    @property
    def gateway_port(self) -> int:
        return int(self.gateway_endpoint.rsplit(":",1)[1])

    def fingerprint(self)->str:
        canonical=json.dumps(self.__dict__,sort_keys=True,separators=(",",":")).encode()
        return hashlib.sha256(canonical).hexdigest()
