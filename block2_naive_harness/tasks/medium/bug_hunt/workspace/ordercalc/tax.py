from ordercalc.discounts import percent_off

TAX_RATE_PCT = 8


def tax_cents(taxable_cents: int) -> int:
    return percent_off(taxable_cents, TAX_RATE_PCT)
