"""Reconcile the loans_payable account against an external statement."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "loans_payable"


def reconcile_loans_payable(ledger, statement_total: str) -> dict:
    ours = balance_of(ledger, ACCOUNT)
    theirs = to_minor(statement_total)
    return {"account": ACCOUNT, "ours": ours, "theirs": theirs, "delta": ours - theirs}
