"""Exposure limit check for the rent_expense account."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "rent_expense"
DEFAULT_LIMIT = "1000000.00"


def within_limit_rent_expense(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(balance_of(ledger, ACCOUNT)) <= to_minor(limit)
