"""Explicit, integer-only order pricing rules for the quality-gate demo."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

REGULAR_SHIPPING_CENTS = 500
EXPRESS_SHIPPING_CENTS = 1_200
FREE_SHIPPING_THRESHOLD_CENTS = 5_000
PREMIUM_DISCOUNT_PERCENT = 5
MAX_COUPON_PERCENT = 30


class PricingError(ValueError):
    """Raised when an order request violates the public pricing contract."""


class Membership(StrEnum):
    """Supported membership tiers."""

    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass(frozen=True, slots=True)
class Quote:
    """Auditable price breakdown, represented in integer cents."""

    subtotal_cents: int
    coupon_discount_cents: int
    membership_discount_cents: int
    shipping_cents: int
    total_cents: int

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-compatible breakdown."""

        return asdict(self)


def quote_order(
    *,
    subtotal_cents: int,
    membership: Membership,
    coupon_percent: int = 0,
    express: bool = False,
) -> Quote:
    """Apply coupon, membership, and shipping rules in that order."""

    _validate_request(subtotal_cents, membership, coupon_percent, express)

    coupon_discount = subtotal_cents * coupon_percent // 100
    after_coupon = subtotal_cents - coupon_discount
    membership_discount = (
        after_coupon * PREMIUM_DISCOUNT_PERCENT // 100 if membership is Membership.PREMIUM else 0
    )
    merchandise_total = after_coupon - membership_discount
    shipping = _shipping_cost(merchandise_total, express)

    return Quote(
        subtotal_cents=subtotal_cents,
        coupon_discount_cents=coupon_discount,
        membership_discount_cents=membership_discount,
        shipping_cents=shipping,
        total_cents=merchandise_total + shipping,
    )


def _validate_request(
    subtotal_cents: int,
    membership: Membership,
    coupon_percent: int,
    express: bool,
) -> None:
    _validate_subtotal(subtotal_cents)
    _validate_coupon(coupon_percent)
    if not isinstance(membership, Membership):
        raise PricingError("membership must be a Membership value")
    if not isinstance(express, bool):
        raise PricingError("express must be boolean")


def _validate_subtotal(subtotal_cents: int) -> None:
    if (
        isinstance(subtotal_cents, bool)
        or not isinstance(subtotal_cents, int)
        or subtotal_cents <= 0
    ):
        raise PricingError("subtotal_cents must be a positive integer")


def _validate_coupon(coupon_percent: int) -> None:
    if (
        isinstance(coupon_percent, bool)
        or not isinstance(coupon_percent, int)
        or not 0 <= coupon_percent <= MAX_COUPON_PERCENT
    ):
        raise PricingError("coupon_percent must be an integer from 0 to 30")


def _shipping_cost(merchandise_total: int, express: bool) -> int:
    if express:
        return EXPRESS_SHIPPING_CENTS
    if merchandise_total >= FREE_SHIPPING_THRESHOLD_CENTS:
        return 0
    return REGULAR_SHIPPING_CENTS
