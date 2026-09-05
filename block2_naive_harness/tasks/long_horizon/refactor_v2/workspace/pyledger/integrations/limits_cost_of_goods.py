"""Exposure limit check for the cost_of_goods account."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "cost_of_goods"
DEFAULT_LIMIT = "1000000.00"


def within_limit_cost_of_goods(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(balance_of(ledger, ACCOUNT)) <= to_minor(limit)
