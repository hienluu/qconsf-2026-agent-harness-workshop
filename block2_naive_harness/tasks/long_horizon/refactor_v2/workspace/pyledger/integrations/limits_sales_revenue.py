"""Exposure limit check for the sales_revenue account."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "sales_revenue"
DEFAULT_LIMIT = "1000000.00"


def within_limit_sales_revenue(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(balance_of(ledger, ACCOUNT)) <= to_minor(limit)
