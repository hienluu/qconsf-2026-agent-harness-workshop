from ordercalc.loyalty import points_earned, points_value_cents
from ordercalc.shipping import shipping_cents


def test_flat_rate_below_threshold():
    assert shipping_cents(4999) == 599


def test_free_shipping_at_threshold():
    assert shipping_cents(5000) == 0


def test_points_earned_per_dollar():
    assert points_earned(3210) == 64


def test_points_redeem_value():
    assert points_value_cents(64) == 64
