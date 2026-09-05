"""Naive monthly run-rate forecast for the service_revenue account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.dates import month_key

ACCOUNT = "service_revenue"


def run_rate_service_revenue(ledger) -> int:
    months = {}
    for e in entries_for(ledger, ACCOUNT):
        months.setdefault(month_key(e.date), 0)
        months[month_key(e.date)] += e.signed()
    if not months:
        return 0
    return sum(months.values()) // len(months)
