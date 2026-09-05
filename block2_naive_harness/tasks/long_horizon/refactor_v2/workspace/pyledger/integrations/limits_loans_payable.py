"""Exposure limit check for the loans_payable account."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "loans_payable"
DEFAULT_LIMIT = "1000000.00"


def within_limit_loans_payable(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(get_balance(ledger, ACCOUNT)) <= to_cents(limit)
