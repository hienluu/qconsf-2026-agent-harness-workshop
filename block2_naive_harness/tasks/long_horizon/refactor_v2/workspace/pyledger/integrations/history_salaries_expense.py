"""Chronological activity trail for the salaries_expense account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.dates import month_key

ACCOUNT = "salaries_expense"


def history_salaries_expense(ledger) -> list:
    trail = []
    for e in entries_by_account(ledger, ACCOUNT):
        trail.append((month_key(e.date), e.side, e.amt))
    return trail
