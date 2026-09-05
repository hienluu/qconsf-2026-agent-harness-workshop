"""Reconcile the cost_of_goods account against an external statement."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "cost_of_goods"


def reconcile_cost_of_goods(ledger, statement_total: str) -> dict:
    ours = get_balance(ledger, ACCOUNT)
    theirs = to_cents(statement_total)
    return {"account": ACCOUNT, "ours": ours, "theirs": theirs, "delta": ours - theirs}
