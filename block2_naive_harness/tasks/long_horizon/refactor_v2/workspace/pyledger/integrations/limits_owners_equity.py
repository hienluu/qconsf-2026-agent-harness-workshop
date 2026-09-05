"""Exposure limit check for the owners_equity account."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "owners_equity"
DEFAULT_LIMIT = "1000000.00"


def within_limit_owners_equity(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(get_balance(ledger, ACCOUNT)) <= to_cents(limit)
