import csv

from pyledger.core.entry import Entry

COLUMNS = ["entry_id", "date", "account", "amt", "side", "memo"]


def load_entries_csv(path) -> list:
    """Load entries from a CSV file with the standard column set."""
    out = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            out.append(
                Entry(
                    entry_id=row["entry_id"],
                    date=row["date"],
                    account=row["account"],
                    amt=int(row["amt"]),
                    side=row["side"],
                    memo=row.get("memo", ""),
                )
            )
    return out


def dump_entries_csv(path, entries) -> None:
    """Persist entries to a CSV file with the standard column set."""
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for e in entries:
            writer.writerow(
                {
                    "entry_id": e.entry_id,
                    "date": e.date,
                    "account": e.account,
                    "amt": e.amt,
                    "side": e.side,
                    "memo": e.memo,
                }
            )
