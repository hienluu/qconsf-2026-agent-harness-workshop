"""Memo index for the service_revenue account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.money import fmt_amt

ACCOUNT = "service_revenue"


def memo_index_service_revenue(ledger) -> list:
    out = []
    for e in entries_by_account(ledger, ACCOUNT):
        if e.memo:
            out.append(f"{e.entry_id}: {e.memo} ({fmt_amt(e.amt)})")
    return out
