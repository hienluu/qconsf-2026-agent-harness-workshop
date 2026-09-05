"""Reconcile the loans_payable account against an external statement."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "loans_payable"


def reconcile_loans_payable(ledger, statement_total: str) -> dict:
    ours = get_balance(ledger, ACCOUNT)
    theirs = to_cents(statement_total)
    return {"account": ACCOUNT, "ours": ours, "theirs": theirs, "delta": ours - theirs}
