"""Bulk import: CSV files straight into a fresh ledger."""

from pyledger.core.ledger import new_ledger, record
from pyledger.ledger_io.csv_io import read_entries_csv


def import_csv(name: str, path):
    ledger = new_ledger(name)
    for entry in read_entries_csv(path):
        record(ledger, entry)
    return ledger
