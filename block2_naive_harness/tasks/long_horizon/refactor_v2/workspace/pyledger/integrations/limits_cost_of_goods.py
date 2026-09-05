"""Exposure limit check for the cost_of_goods account."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "cost_of_goods"
DEFAULT_LIMIT = "1000000.00"


def within_limit_cost_of_goods(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(get_balance(ledger, ACCOUNT)) <= to_cents(limit)
