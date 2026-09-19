"""Minimal command line for pyledger: load a CSV and print a summary."""

import argparse

from pyledger.core.ledger import make_ledger, post
from pyledger.ledger_io.csv_io import load_entries_csv
from pyledger.reports.summary import render_summary
from pyledger.reports.trial_balance import balanced


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pyledger")
    parser.add_argument("csv_path")
    parser.add_argument("--name", default="ledger")
    args = parser.parse_args(argv)

    ledger = make_ledger(args.name)
    for entry in load_entries_csv(args.csv_path):
        post(ledger, entry)

    print(render_summary(ledger))
    print("balanced" if balanced(ledger) else "NOT BALANCED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
