"""Exposure limit check for the inventory account."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "inventory"
DEFAULT_LIMIT = "1000000.00"


def within_limit_inventory(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(get_balance(ledger, ACCOUNT)) <= to_cents(limit)
