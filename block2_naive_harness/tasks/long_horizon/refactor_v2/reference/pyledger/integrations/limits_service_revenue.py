"""Exposure limit check for the service_revenue account."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "service_revenue"
DEFAULT_LIMIT = "1000000.00"


def within_limit_service_revenue(ledger, limit: str = DEFAULT_LIMIT) -> bool:
    return abs(get_balance(ledger, ACCOUNT)) <= to_cents(limit)
