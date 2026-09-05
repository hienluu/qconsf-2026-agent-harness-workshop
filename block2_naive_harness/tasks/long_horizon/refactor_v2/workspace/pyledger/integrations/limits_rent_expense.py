"""Exposure limit check for the rent_expense account."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "rent_expense"
DEFAULT_LIMIT = "1000000.00"


def within_limit_rent_expense(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(get_balance(ledger, ACCOUNT)) <= to_cents(limit)
