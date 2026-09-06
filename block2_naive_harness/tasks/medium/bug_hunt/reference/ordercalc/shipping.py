FREE_SHIPPING_THRESHOLD_CENTS = 5000
FLAT_RATE_CENTS = 599


def shipping_cents(subtotal_cents: int) -> int:
    if subtotal_cents >= FREE_SHIPPING_THRESHOLD_CENTS:
        return 0
    return FLAT_RATE_CENTS
