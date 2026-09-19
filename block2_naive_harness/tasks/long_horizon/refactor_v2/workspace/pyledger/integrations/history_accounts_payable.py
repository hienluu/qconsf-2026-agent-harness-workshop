"""Chronological activity trail for the accounts_payable account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.dates import month_key

ACCOUNT = "accounts_payable"


def history_accounts_payable(ledger) -> list:
    trail = []
    for e in entries_for(ledger, ACCOUNT):
        trail.append((month_key(e.date), e.kind, e.amount))
    return trail
