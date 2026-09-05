"""Memo index for the salaries_expense account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.money import fmt_amt

ACCOUNT = "salaries_expense"


def memo_index_salaries_expense(ledger) -> list:
    out = []
    for e in entries_by_account(ledger, ACCOUNT):
        if e.memo:
            out.append(f"{e.entry_id}: {e.memo} ({fmt_amt(e.amt)})")
    return out
