from __future__ import annotations

from behave import given, then, when

from quality_gate_demo.pricing import Membership, Quote, quote_order


@given("a {membership} member has an order subtotal of {subtotal:d} cents")
def given_order(context: object, membership: str, subtotal: int) -> None:
    context.subtotal = subtotal  # type: ignore[attr-defined]
    context.membership = Membership(membership)  # type: ignore[attr-defined]
    context.coupon = 0  # type: ignore[attr-defined]
    context.express = False  # type: ignore[attr-defined]


@given("the coupon discount is {percent:d} percent")
def given_coupon(context: object, percent: int) -> None:
    context.coupon = percent  # type: ignore[attr-defined]


@given("express shipping is requested")
def given_express(context: object) -> None:
    context.express = True  # type: ignore[attr-defined]


@when("the order is quoted")
def when_quoted(context: object) -> None:
    context.quote = quote_order(  # type: ignore[attr-defined]
        subtotal_cents=context.subtotal,  # type: ignore[attr-defined]
        membership=context.membership,  # type: ignore[attr-defined]
        coupon_percent=context.coupon,  # type: ignore[attr-defined]
        express=context.express,  # type: ignore[attr-defined]
    )


def quote_from(context: object) -> Quote:
    return context.quote  # type: ignore[attr-defined, no-any-return]


@then("the total is {total:d} cents")
def then_total(context: object, total: int) -> None:
    assert quote_from(context).total_cents == total


@then("the coupon discount is {discount:d} cents")
def then_coupon(context: object, discount: int) -> None:
    assert quote_from(context).coupon_discount_cents == discount


@then("the membership discount is {discount:d} cents")
def then_membership(context: object, discount: int) -> None:
    assert quote_from(context).membership_discount_cents == discount


@then("shipping is free")
def then_free_shipping(context: object) -> None:
    assert quote_from(context).shipping_cents == 0


@then("shipping costs {shipping:d} cents")
def then_shipping(context: object, shipping: int) -> None:
    assert quote_from(context).shipping_cents == shipping
