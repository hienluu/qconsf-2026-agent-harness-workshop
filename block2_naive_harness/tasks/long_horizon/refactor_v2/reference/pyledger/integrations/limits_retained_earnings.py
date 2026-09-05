"""Exposure limit check for the retained_earnings account."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "retained_earnings"
DEFAULT_LIMIT = "1000000.00"


def within_limit_retained_earnings(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(get_balance(ledger, ACCOUNT)) <= to_cents(limit)
