"""Memo index for the equipment account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.money import format_amount

ACCOUNT = "equipment"


def memo_index_equipment(ledger) -> list:
    out = []
    for e in entries_for(ledger, ACCOUNT):
        if e.memo:
            out.append(f"{e.entry_id}: {e.memo} ({format_amount(e.amount)})")
    return out
