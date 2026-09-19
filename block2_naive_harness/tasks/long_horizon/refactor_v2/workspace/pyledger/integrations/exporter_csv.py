"""Bulk export: one account's entries to a CSV file."""

from pyledger.core.ledger import entries_for
from pyledger.ledger_io.csv_io import write_entries_csv


def export_account_csv(ledger, account: str, path) -> int:
    entries = entries_for(ledger, account)
    write_entries_csv(path, entries)
    return len(entries)
