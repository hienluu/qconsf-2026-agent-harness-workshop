"""Exporter for the inventory account."""

from pyledger.core.ledger import get_balance, entries_for
from pyledger.utils.money import format_amount

ACCOUNT = "inventory"


def export_inventory(ledger) -> str:
    lines = [f"{ACCOUNT}: {format_amount(get_balance(ledger, ACCOUNT))}"]
    for e in entries_for(ledger, ACCOUNT):
        lines.append(f"  {e.entry_id} {e.date} {e.kind} {format_amount(e.amount)}")
    return "\n".join(lines)


def debit_total_inventory(ledger) -> int:
    return sum(e.amount for e in entries_for(ledger, ACCOUNT) if e.kind == "debit")


def credit_total_inventory(ledger) -> int:
    return sum(e.amount for e in entries_for(ledger, ACCOUNT) if e.kind == "credit")
