"""Command-line adapter for the example pricing policy."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from quality_gate_demo.pricing import Membership, PricingError, quote_order

ALLOWED_FIELDS = {"subtotal_cents", "membership", "coupon_percent", "express"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Quote a sample order")
    subparsers = parser.add_subparsers(dest="command", required=True)
    quote_parser = subparsers.add_parser("quote", help="quote an order from JSON")
    quote_parser.add_argument("--input", required=True, type=Path, help="path to the order JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = _read_payload(args.input)
        quote = quote_order(
            subtotal_cents=payload["subtotal_cents"],
            membership=Membership(payload["membership"]),
            coupon_percent=payload.get("coupon_percent", 0),
            express=payload.get("express", False),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, PricingError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(quote.to_dict(), indent=2, sort_keys=True))
    return 0


def _read_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("input must be a JSON object")
    unknown_fields = set(payload) - ALLOWED_FIELDS
    if unknown_fields:
        raise ValueError(f"unknown field: {sorted(unknown_fields)[0]}")
    return payload
