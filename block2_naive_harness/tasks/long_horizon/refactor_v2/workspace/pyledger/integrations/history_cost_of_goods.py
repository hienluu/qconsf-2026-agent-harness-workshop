"""Chronological activity trail for the cost_of_goods account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.dates import month_key

ACCOUNT = "cost_of_goods"


def history_cost_of_goods(ledger) -> list:
    trail = []
    for e in entries_for(ledger, ACCOUNT):
        trail.append((month_key(e.date), e.kind, e.amount))
    return trail
