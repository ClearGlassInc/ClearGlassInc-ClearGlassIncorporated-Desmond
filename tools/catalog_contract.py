#!/usr/bin/env python3
"""The canonical product-catalog contract, and a validator that reports gaps.

A governed checkout is supposed to reject any request whose SKU, amount,
currency or product type does not match the approved catalog. That check is
only as good as the catalog behind it, and this repository has three catalogs
with three different shapes:

* ``control-plane/app/data/pricebook.json`` — the **server-side price
  authority**. ``POST /checkout/session`` resolves amounts here and nowhere
  else, so this is the file that actually decides what a customer is charged.
* ``data/store/catalog.json`` — five service engagements with live
  ``buy.stripe.com`` URLs, rendered by the static site.
* ``data/side-store/catalog.json`` — 57 impulse SKUs, projected out of
  ``side-store.html`` by ``tools/side_store_catalog.py``.

None of them carries the full field set a governed catalog needs. Product type,
tax and shipping policy, fulfillment type, delivery entitlement, inventory
source and refund policy are absent or partial everywhere, so "reject anything
that does not match the catalog" cannot be fully enforced: the catalog has no
field to check against.

This module states the contract and measures the distance to it. It
deliberately **invents nothing**. Where a field is missing it is reported as
missing, because the correct value is a business decision — what a SKU's refund
policy is, or whether an engagement is a service or a subscription, is not
something a tool may guess.

Usage::

    python3 tools/catalog_contract.py              # gap report, always exit 0
    python3 tools/catalog_contract.py --json       # machine-readable
    python3 tools/catalog_contract.py --strict     # exit 1 if any SKU is incomplete

``--strict`` is the future gate. It is not wired into ``scripts/ci_local.py``
or ``ci.yml`` yet, and must not be until the owner has supplied the missing
values — turning it on now would only break the build to report something this
file already reports.

Stdlib only, so it runs in the same minimal environments as the other
generators.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass, field

REPO = pathlib.Path(__file__).resolve().parent.parent

PRODUCT_TYPES = ("digital", "physical", "subscription", "service")


@dataclass(frozen=True)
class Field:
    """One canonical field, and the existing key names that already carry it.

    ``aliases`` is how a catalog satisfies a field without being rewritten:
    ``pricebook.json`` already stores the approved price under ``amount``, so
    that counts. An alias is only listed where the meaning is unambiguous —
    guessing an equivalence would defeat the point of the check.
    """

    name: str
    required: bool
    why: str
    aliases: tuple[str, ...] = ()


CONTRACT: tuple[Field, ...] = (
    Field("sku", True, "The join key across catalog, order, processor and ledger.",
          ("id",)),
    Field("product_name", True, "What the customer is told they bought.",
          ("name", "label")),
    Field("product_type", True,
          f"One of {', '.join(PRODUCT_TYPES)}. Decides which fulfillment path may run."),
    Field("approved_price", True,
          "Integer minor units. The only amount a checkout may charge.",
          ("amount_cents", "amount", "price")),
    Field("currency", True, "ISO 4217. A price without one is not a price."),
    Field("tax_policy", True,
          "How tax is applied. Stripe rejects session creation when this is unsettled.",
          ("tax_behavior",)),
    Field("shipping_policy", False, "Required for physical goods; omit for digital."),
    Field("fulfillment_type", True,
          "What happens after a verified payment. Without it, fulfillment is improvised."),
    Field("delivery_entitlement", False,
          "For digital goods: what access the buyer is granted, and for how long."),
    Field("inventory_source", True,
          "Where stock is authoritative. Absent, an oversell cannot be detected."),
    Field("active", True, "Whether the SKU may be sold right now."),
    Field("refund_policy_ref", True,
          "Pointer to the published policy the buyer agreed to."),
    Field("stripe_price_id", False, "Stripe's own price authority, where applicable.",
          ("stripe_price",)),
    Field("etsy_listing_id", False, "Etsy listing this SKU maps to, where applicable."),
    Field("paypal_reference_id", False, "PayPal item/reference id, where applicable."),
)

CATALOGS: tuple[tuple[str, str], ...] = (
    ("control-plane/app/data/pricebook.json", "offers"),
    ("data/store/catalog.json", "products"),
    ("data/side-store/catalog.json", "items"),
)


@dataclass
class SkuReport:
    sku: str
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    satisfied_by_alias: dict[str, str] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return not self.missing_required


def _entries(path: pathlib.Path, key: str) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, list):
        return [e for e in doc if isinstance(e, dict)]
    return [e for e in doc.get(key, []) if isinstance(e, dict)]


def audit_entry(entry: dict) -> SkuReport:
    """Measure one catalog entry against the contract. Never mutates it."""
    rep = SkuReport(sku=str(entry.get("sku") or entry.get("id") or "<no sku>"))
    for f in CONTRACT:
        if f.name in entry:
            continue
        alias = next((a for a in f.aliases if a in entry), None)
        if alias is not None:
            rep.satisfied_by_alias[f.name] = alias
            continue
        (rep.missing_required if f.required else rep.missing_optional).append(f.name)
    return rep


def audit_catalog(rel: str, key: str) -> tuple[str, list[SkuReport], str | None]:
    path = REPO / rel
    if not path.exists():
        return rel, [], "file not found"
    try:
        return rel, [audit_entry(e) for e in _entries(path, key)], None
    except (json.JSONDecodeError, OSError) as exc:
        return rel, [], f"unreadable: {type(exc).__name__}: {exc}"


def audit_all() -> list[tuple[str, list[SkuReport], str | None]]:
    return [audit_catalog(rel, key) for rel, key in CATALOGS]


def _render(results) -> int:
    incomplete = 0
    for rel, reports, err in results:
        print(f"\n{rel}")
        if err:
            print(f"  ! {err}")
            continue
        if not reports:
            print("  (no entries)")
            continue
        gaps: dict[str, int] = {}
        for r in reports:
            if not r.complete:
                incomplete += 1
            for m in r.missing_required:
                gaps[m] = gaps.get(m, 0) + 1
        print(f"  entries              : {len(reports)}")
        print(f"  contract-complete    : {sum(1 for r in reports if r.complete)}")
        if gaps:
            print("  required fields missing (SKUs affected):")
            for name, n in sorted(gaps.items(), key=lambda kv: (-kv[1], kv[0])):
                why = next(f.why for f in CONTRACT if f.name == name)
                print(f"    {name:22} {n:>3}   {why}")
        aliases = {k: v for r in reports for k, v in r.satisfied_by_alias.items()}
        if aliases:
            print("  satisfied by existing keys:")
            for canon, alias in sorted(aliases.items()):
                print(f"    {canon:22} <- {alias}")
    print(f"\nSKUs not contract-complete: {incomplete}")
    if incomplete:
        print("No value was guessed. Each missing field is a business decision;")
        print("see docs/CATALOG_SCHEMA.md for what the owner must supply.")
    return incomplete


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any SKU is not contract-complete")
    args = ap.parse_args()

    results = audit_all()
    if args.json:
        print(json.dumps({
            "catalogs": [
                {"path": rel, "error": err,
                 "skus": [{"sku": r.sku, "complete": r.complete,
                           "missing_required": r.missing_required,
                           "missing_optional": r.missing_optional,
                           "satisfied_by_alias": r.satisfied_by_alias}
                          for r in reports]}
                for rel, reports, err in results
            ]
        }, indent=2))
        incomplete = sum(1 for _, reps, _ in results for r in reps if not r.complete)
    else:
        incomplete = _render(results)
    return 1 if (args.strict and incomplete) else 0


if __name__ == "__main__":
    sys.exit(main())
