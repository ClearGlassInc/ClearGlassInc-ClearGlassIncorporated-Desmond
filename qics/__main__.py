"""CLI: python -m qics --tenant demo --inventory path.json"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .commander import QuantumCommander
from .schema import Inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qics", description="ClearGlass QICS scanner")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--inventory", help="JSON file with {assets, inventory_complete, ...}")
    parser.add_argument("--actor", default="operator")
    args = parser.parse_args(argv)

    data: dict = {}
    if args.inventory:
        data = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    inventory = Inventory(
        tenant_id=args.tenant,
        assets=list(data.get("assets") or []),
        inventory_complete=bool(data.get("inventory_complete", False)),
        long_lived_sensitive_data=data.get("long_lived_sensitive_data"),
        crypto_agile=data.get("crypto_agile"),
    )
    result = QuantumCommander().run(inventory, actor=args.actor)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
