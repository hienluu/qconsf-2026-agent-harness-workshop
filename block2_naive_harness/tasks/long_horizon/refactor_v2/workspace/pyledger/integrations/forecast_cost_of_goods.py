"""Naive monthly run-rate forecast for the cost_of_goods account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.dates import month_key

ACCOUNT = "cost_of_goods"


def run_rate_cost_of_goods(ledger) -> int:
    months = {}
    for e in entries_for(ledger, ACCOUNT):
        months.setdefault(month_key(e.date), 0)
        months[month_key(e.date)] += e.signed()
    if not months:
        return 0
    return sum(months.values()) // len(months)
