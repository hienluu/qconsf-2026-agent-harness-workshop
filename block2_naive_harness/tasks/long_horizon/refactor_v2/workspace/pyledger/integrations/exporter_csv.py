"""Bulk export: one account's entries to a CSV file."""

from pyledger.core.ledger import entries_by_account
from pyledger.ledger_io.csv_io import dump_entries_csv


def export_account_csv(ledger, account: str, path) -> int:
    entries = entries_by_account(ledger, account)
    dump_entries_csv(path, entries)
    return len(entries)
