"""Minimal command line for pyledger: load a CSV and print a summary."""

import argparse

from pyledger.core.ledger import new_ledger, record
from pyledger.ledger_io.csv_io import read_entries_csv
from pyledger.reports.summary import render_summary
from pyledger.reports.trial_balance import is_balanced


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pyledger")
    parser.add_argument("csv_path")
    parser.add_argument("--name", default="ledger")
    args = parser.parse_args(argv)

    ledger = new_ledger(args.name)
    for entry in read_entries_csv(args.csv_path):
        record(ledger, entry)

    print(render_summary(ledger))
    print("balanced" if is_balanced(ledger) else "NOT BALANCED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
