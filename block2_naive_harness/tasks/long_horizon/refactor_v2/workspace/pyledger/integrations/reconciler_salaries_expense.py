"""Reconcile the salaries_expense account against an external statement."""

from pyledger.core.ledger import get_balance
from pyledger.utils.money import to_cents

ACCOUNT = "salaries_expense"


def reconcile_salaries_expense(ledger, statement_total: str) -> dict:
    ours = get_balance(ledger, ACCOUNT)
    theirs = to_cents(statement_total)
    return {"account": ACCOUNT, "ours": ours, "theirs": theirs, "delta": ours - theirs}
