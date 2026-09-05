"""Memo index for the accounts_receivable account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.money import format_amount

ACCOUNT = "accounts_receivable"


def memo_index_accounts_receivable(ledger) -> list:
    out = []
    for e in entries_for(ledger, ACCOUNT):
        if e.memo:
            out.append(f"{e.entry_id}: {e.memo} ({format_amount(e.amount)})")
    return out
