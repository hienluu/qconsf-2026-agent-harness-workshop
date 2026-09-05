"""Memo index for the utilities_expense account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.money import format_amount

ACCOUNT = "utilities_expense"


def memo_index_utilities_expense(ledger) -> list:
    out = []
    for e in entries_for(ledger, ACCOUNT):
        if e.memo:
            out.append(f"{e.entry_id}: {e.memo} ({format_amount(e.amount)})")
    return out
