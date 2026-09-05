"""Naive monthly run-rate forecast for the salaries_expense account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.dates import month_key

ACCOUNT = "salaries_expense"


def run_rate_salaries_expense(ledger) -> int:
    months = {}
    for e in entries_by_account(ledger, ACCOUNT):
        months.setdefault(month_key(e.date), 0)
        months[month_key(e.date)] += e.signed()
    if not months:
        return 0
    return sum(months.values()) // len(months)
