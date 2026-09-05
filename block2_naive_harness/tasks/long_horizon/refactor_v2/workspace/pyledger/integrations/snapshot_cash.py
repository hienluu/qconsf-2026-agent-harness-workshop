"""Point-in-time snapshot of the cash account."""

from pyledger.core.ledger import entries_for, get_balance
from pyledger.utils.money import from_cents

ACCOUNT = "cash"


def snapshot_cash(ledger) -> dict:
    entries = entries_for(ledger, ACCOUNT)
    return {
        "account": ACCOUNT,
        "entry_count": len(entries),
        "net": from_cents(get_balance(ledger, ACCOUNT)),
        "last_date": entries[-1].date if entries else None,
    }
