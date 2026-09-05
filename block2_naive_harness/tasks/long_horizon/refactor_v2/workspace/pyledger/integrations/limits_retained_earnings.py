"""Exposure limit check for the retained_earnings account."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "retained_earnings"
DEFAULT_LIMIT = "1000000.00"


def within_limit_retained_earnings(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(balance_of(ledger, ACCOUNT)) <= to_minor(limit)
