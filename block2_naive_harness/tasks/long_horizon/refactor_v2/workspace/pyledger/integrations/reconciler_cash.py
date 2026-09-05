"""Reconcile the cash account against an external statement."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "cash"


def reconcile_cash(ledger, statement_total: str) -> dict:
    ours = get_balance(ledger, ACCOUNT)
    theirs = to_cents(statement_total)
    return {"account": ACCOUNT, "ours": ours, "theirs": theirs, "delta": ours - theirs}
