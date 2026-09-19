"""Chronological activity trail for the retained_earnings account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.dates import month_key

ACCOUNT = "retained_earnings"


def history_retained_earnings(ledger) -> list:
    trail = []
    for e in entries_by_account(ledger, ACCOUNT):
        trail.append((month_key(e.date), e.side, e.amt))
    return trail
