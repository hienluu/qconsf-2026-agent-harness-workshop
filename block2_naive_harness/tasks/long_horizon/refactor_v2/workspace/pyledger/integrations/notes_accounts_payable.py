"""Memo index for the accounts_payable account."""

from pyledger.core.ledger import entries_by_account
from pyledger.utils.money import fmt_amt

ACCOUNT = "accounts_payable"


def memo_index_accounts_payable(ledger) -> list:
    out = []
    for e in entries_by_account(ledger, ACCOUNT):
        if e.memo:
            out.append(f"{e.entry_id}: {e.memo} ({fmt_amt(e.amt)})")
    return out
