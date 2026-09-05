"""Chronological activity trail for the sales_revenue account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.dates import month_key

ACCOUNT = "sales_revenue"


def history_sales_revenue(ledger) -> list:
    trail = []
    for e in entries_by_account(ledger, ACCOUNT):
        trail.append((month_key(e.date), e.side, e.amt))
    return trail
