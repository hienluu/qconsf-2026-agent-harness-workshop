"""Exporter for the accounts_payable account."""

from pyledger.core.ledger import balance_of, entries_by_account
from pyledger.utils.money import fmt_amt

ACCOUNT = "accounts_payable"


def export_accounts_payable(ledger) -> str:
    lines = [f"{ACCOUNT}: {fmt_amt(balance_of(ledger, ACCOUNT))}"]
    for e in entries_by_account(ledger, ACCOUNT):
        lines.append(f"  {e.entry_id} {e.date} {e.side} {fmt_amt(e.amt)}")
    return "\n".join(lines)


def debit_total_accounts_payable(ledger) -> int:
    return sum(e.amt for e in entries_by_account(ledger, ACCOUNT) if e.side == "debit")


def credit_total_accounts_payable(ledger) -> int:
    return sum(e.amt for e in entries_by_account(ledger, ACCOUNT) if e.side == "credit")
