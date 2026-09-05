"""Chronological activity trail for the inventory account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.dates import month_key

ACCOUNT = "inventory"


def history_inventory(ledger) -> list:
    trail = []
    for e in entries_by_account(ledger, ACCOUNT):
        trail.append((month_key(e.date), e.side, e.amt))
    return trail
