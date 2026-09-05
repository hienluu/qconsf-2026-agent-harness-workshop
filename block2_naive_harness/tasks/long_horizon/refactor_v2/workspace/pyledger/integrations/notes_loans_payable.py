"""Memo index for the loans_payable account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.money import format_amount

ACCOUNT = "loans_payable"


def memo_index_loans_payable(ledger) -> list:
    out = []
    for e in entries_for(ledger, ACCOUNT):
        if e.memo:
            out.append(f"{e.entry_id}: {e.memo} ({format_amount(e.amount)})")
    return out
