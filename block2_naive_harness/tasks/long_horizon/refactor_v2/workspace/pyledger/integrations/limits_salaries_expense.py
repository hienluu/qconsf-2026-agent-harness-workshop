"""Exposure limit check for the salaries_expense account."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "salaries_expense"
DEFAULT_LIMIT = "1000000.00"


def within_limit_salaries_expense(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(balance_of(ledger, ACCOUNT)) <= to_minor(limit)
