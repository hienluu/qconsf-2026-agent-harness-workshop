"""Point-in-time snapshot of the utilities_expense account."""

from pyledger.core.ledger import entries_by_account, balance_of
from pyledger.utils.money import from_minor

ACCOUNT = "utilities_expense"


def snapshot_utilities_expense(ledger) -> dict:
    entries = entries_by_account(ledger, ACCOUNT)
    return {
        "account": ACCOUNT,
        "entry_count": len(entries),
        "net": from_minor(balance_of(ledger, ACCOUNT)),
        "last_date": entries[-1].date if entries else None,
    }
