"""Chronological activity trail for the accounts_receivable account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.dates import month_key

ACCOUNT = "accounts_receivable"


def history_accounts_receivable(ledger) -> list:
    trail = []
    for e in entries_for(ledger, ACCOUNT):
        trail.append((month_key(e.date), e.kind, e.amount))
    return trail
