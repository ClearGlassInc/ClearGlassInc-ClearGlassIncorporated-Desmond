from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from pathlib import Path

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
        if missing: raise ValueError("missing configuration fields: "+str(sorted(missing)))
        if data["environment"]!="isolated-disposable-test": raise ValueError("refusing non-test environment")
        if data["network_lock"] is not True: raise ValueError("test configuration must enable network lock")
        return cls(**{k:data[k] for k in required})

    def fingerprint(self)->str:
        canonical=json.dumps(self.__dict__,sort_keys=True,separators=(",",":")).encode()
        return hashlib.sha256(canonical).hexdigest()
