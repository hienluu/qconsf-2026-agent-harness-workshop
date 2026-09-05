"""Exposure limit check for the loans_payable account."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "loans_payable"
DEFAULT_LIMIT = "1000000.00"


def within_limit_loans_payable(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(balance_of(ledger, ACCOUNT)) <= to_minor(limit)
