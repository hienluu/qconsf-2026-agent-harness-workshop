"""Bulk import: CSV files straight into a fresh ledger."""

from pyledger.core.ledger import make_ledger, post
from pyledger.ledger_io.csv_io import load_entries_csv


def import_csv(name: str, path):
    ledger = make_ledger(name)
    for entry in load_entries_csv(path):
        post(ledger, entry)
    return ledger
