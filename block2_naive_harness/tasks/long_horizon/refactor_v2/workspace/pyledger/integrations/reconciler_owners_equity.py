"""Reconcile the owners_equity account against an external statement."""

from pyledger.core.ledger import balance_of
from pyledger.utils.money import to_minor

ACCOUNT = "owners_equity"


def reconcile_owners_equity(ledger, statement_total: str) -> dict:
    ours = balance_of(ledger, ACCOUNT)
    theirs = to_minor(statement_total)
    return {"account": ACCOUNT, "ours": ours, "theirs": theirs, "delta": ours - theirs}
