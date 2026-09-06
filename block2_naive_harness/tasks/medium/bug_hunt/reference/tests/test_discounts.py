import pytest

from ordercalc import Cart, LineItem
from ordercalc.discounts import bulk_discount_cents, coupon_discount_cents, percent_off


def test_percent_off_small_amounts():
    assert percent_off(150, 5) == 8
    assert percent_off(199, 10) == 20


def test_percent_off_exact():
    assert percent_off(1000, 10) == 100


def test_bulk_discount_at_threshold():
    cart = Cart([LineItem("widget", 499, 3), LineItem("gadget", 250, 8)])  # 11 items
    assert bulk_discount_cents(cart) == 350  # 10% of 3497, half-up


def test_no_bulk_discount_below_threshold():
    cart = Cart([LineItem("widget", 499, 9)])
    assert bulk_discount_cents(cart) == 0


def test_unknown_coupon_raises():
    with pytest.raises(KeyError):
        coupon_discount_cents(Cart([LineItem("w", 100, 1)]), "BOGUS")
