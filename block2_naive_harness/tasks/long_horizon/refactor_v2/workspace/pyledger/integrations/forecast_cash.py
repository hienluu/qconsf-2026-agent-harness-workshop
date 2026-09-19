"""Naive monthly run-rate forecast for the cash account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.dates import month_key

ACCOUNT = "cash"


def run_rate_cash(ledger) -> int:
    months = {}
    for e in entries_by_account(ledger, ACCOUNT):
        months.setdefault(month_key(e.date), 0)
        months[month_key(e.date)] += e.signed()
    if not months:
        return 0
    return sum(months.values()) // len(months)
