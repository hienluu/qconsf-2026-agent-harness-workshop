BULK_THRESHOLD = 10   # items
BULK_PCT = 10
COUPONS = {"SAVE5": 5, "SAVE15": 15}


def percent_off(cents: int, pct: int) -> int:
    """Percentage of an amount in cents."""
    return (cents * pct + 50) // 100


def bulk_discount_cents(cart) -> int:
    if cart.item_count() >= BULK_THRESHOLD:
        return percent_off(cart.subtotal_cents(), BULK_PCT)
    return 0


def coupon_discount_cents(cart, coupon: str | None) -> int:
    if coupon is None:
        return 0
    if coupon not in COUPONS:
        raise KeyError(f"unknown coupon: {coupon}")
    return percent_off(cart.subtotal_cents(), COUPONS[coupon])
