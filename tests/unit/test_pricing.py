from __future__ import annotations

import pytest

from quality_gate_demo.pricing import Membership, PricingError, quote_order


def test_standard_order_adds_regular_shipping() -> None:
    quote = quote_order(subtotal_cents=2_000, membership=Membership.STANDARD)

    assert quote.to_dict() == {
        "subtotal_cents": 2_000,
        "coupon_discount_cents": 0,
        "membership_discount_cents": 0,
        "shipping_cents": 500,
        "total_cents": 2_500,
    }


def test_coupon_then_premium_discount_uses_the_remaining_subtotal() -> None:
    quote = quote_order(
        subtotal_cents=6_000,
        membership=Membership.PREMIUM,
        coupon_percent=10,
    )

    assert quote.coupon_discount_cents == 600
    assert quote.membership_discount_cents == 270
    assert quote.shipping_cents == 0
    assert quote.total_cents == 5_130


def test_express_shipping_is_charged_even_above_free_shipping_threshold() -> None:
    quote = quote_order(
        subtotal_cents=6_000,
        membership=Membership.STANDARD,
        express=True,
    )

    assert quote.shipping_cents == 1_200
    assert quote.total_cents == 7_200


def test_fractional_discount_cents_are_rounded_down() -> None:
    quote = quote_order(
        subtotal_cents=101,
        membership=Membership.PREMIUM,
        coupon_percent=10,
    )

    assert quote.coupon_discount_cents == 10
    assert quote.membership_discount_cents == 4
    assert quote.total_cents == 587


def test_one_cent_is_the_smallest_valid_subtotal() -> None:
    quote = quote_order(subtotal_cents=1, membership=Membership.STANDARD)

    assert quote.total_cents == 501


def test_thirty_percent_is_a_valid_coupon_boundary() -> None:
    quote = quote_order(
        subtotal_cents=1_000,
        membership=Membership.STANDARD,
        coupon_percent=30,
    )

    assert quote.coupon_discount_cents == 300


def test_free_shipping_includes_the_exact_threshold() -> None:
    quote = quote_order(subtotal_cents=5_000, membership=Membership.STANDARD)

    assert quote.shipping_cents == 0


@pytest.mark.parametrize("subtotal", [0, -1, True, 10.5])
def test_subtotal_must_be_a_positive_integer(subtotal: object) -> None:
    with pytest.raises(PricingError) as error:
        quote_order(subtotal_cents=subtotal, membership=Membership.STANDARD)  # type: ignore[arg-type]

    assert str(error.value) == "subtotal_cents must be a positive integer"


@pytest.mark.parametrize("coupon", [-1, 31, True, 1.5])
def test_coupon_must_be_an_integer_from_zero_to_thirty(coupon: object) -> None:
    with pytest.raises(PricingError) as error:
        quote_order(
            subtotal_cents=1_000,
            membership=Membership.STANDARD,
            coupon_percent=coupon,  # type: ignore[arg-type]
        )

    assert str(error.value) == "coupon_percent must be an integer from 0 to 30"


def test_membership_must_use_the_enum_contract() -> None:
    with pytest.raises(PricingError) as error:
        quote_order(subtotal_cents=1_000, membership="premium")  # type: ignore[arg-type]

    assert str(error.value) == "membership must be a Membership value"


def test_express_must_be_boolean() -> None:
    with pytest.raises(PricingError) as error:
        quote_order(
            subtotal_cents=1_000,
            membership=Membership.STANDARD,
            express=1,  # type: ignore[arg-type]
        )

    assert str(error.value) == "express must be boolean"
