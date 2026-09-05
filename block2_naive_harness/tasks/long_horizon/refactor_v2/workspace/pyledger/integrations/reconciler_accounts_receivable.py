"""Reconcile the accounts_receivable account against an external statement."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "accounts_receivable"


def reconcile_accounts_receivable(ledger, statement_total: str) -> dict:
    ours = balance_of(ledger, ACCOUNT)
    theirs = to_minor(statement_total)
    return {"account": ACCOUNT, "ours": ours, "theirs": theirs, "delta": ours - theirs}
