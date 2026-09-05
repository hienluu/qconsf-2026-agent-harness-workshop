"""Memo index for the cost_of_goods account."""

from pyledger.core.ledger import entries_for
from pyledger.utils.money import format_amount

ACCOUNT = "cost_of_goods"


def memo_index_cost_of_goods(ledger) -> list:
    out = []
    for e in entries_for(ledger, ACCOUNT):
        if e.memo:
            out.append(f"{e.entry_id}: {e.memo} ({format_amount(e.amount)})")
    return out
