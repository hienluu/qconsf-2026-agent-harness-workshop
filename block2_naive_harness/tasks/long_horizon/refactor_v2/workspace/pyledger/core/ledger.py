from pyledger.core.validation import check_entry


def make_ledger(name: str) -> dict:
    """Create an empty ledger."""
    return {"name": name, "entries": []}


def post(ledger: dict, entry) -> None:
    """Validate an entry, then append it to the ledger."""
    check_entry(entry)
    ledger["entries"].append(entry)


def balance_of(ledger: dict, account: str) -> int:
    """Net position for one account, in integer cents."""
    total = 0
    for entry in ledger["entries"]:
        if entry.account == account:
            total += entry.signed()
    return total


def entries_by_account(ledger: dict, account: str) -> list:
    """All entries posted against one account, in insertion order."""
    return [e for e in ledger["entries"] if e.account == account]
