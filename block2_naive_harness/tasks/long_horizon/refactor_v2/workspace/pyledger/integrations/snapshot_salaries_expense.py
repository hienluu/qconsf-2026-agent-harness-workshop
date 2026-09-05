"""Point-in-time snapshot of the salaries_expense account."""

from pyledger.core.ledger import entries_for, get_balance
from pyledger.utils.money import from_cents

ACCOUNT = "salaries_expense"


def snapshot_salaries_expense(ledger) -> dict:
    entries = entries_for(ledger, ACCOUNT)
    return {
        "account": ACCOUNT,
        "entry_count": len(entries),
        "net": from_cents(get_balance(ledger, ACCOUNT)),
        "last_date": entries[-1].date if entries else None,
    }
