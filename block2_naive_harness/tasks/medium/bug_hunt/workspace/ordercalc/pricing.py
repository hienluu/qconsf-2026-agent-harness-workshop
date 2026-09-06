from ordercalc.discounts import bulk_discount_cents, coupon_discount_cents
from ordercalc.tax import tax_cents


def price_cart(cart, coupon: str | None = None) -> dict:
    """Price a cart with discounts, coupons, and tax."""
    subtotal = cart.subtotal_cents()
    discount = bulk_discount_cents(cart) + coupon_discount_cents(cart, coupon)
    taxable = subtotal - discount
    tax = tax_cents(subtotal)
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": taxable + tax,
    }
