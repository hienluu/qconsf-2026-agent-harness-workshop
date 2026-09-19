from pyledger.core.validation import validate_entry


def new_ledger(name: str) -> dict:
    """Create an empty ledger."""
    return {"name": name, "entries": []}


def record(ledger: dict, entry) -> None:
    """Validate an entry, then append it to the ledger."""
    validate_entry(entry)
    ledger["entries"].append(entry)


def get_balance(ledger: dict, account: str) -> int:
    """Net position for one account, in integer cents."""
    total = 0
    for entry in ledger["entries"]:
        if entry.account == account:
            total += entry.signed()
    return total


def entries_for(ledger: dict, account: str) -> list:
    """All entries recorded against one account, in insertion order."""
    return [e for e in ledger["entries"] if e.account == account]
