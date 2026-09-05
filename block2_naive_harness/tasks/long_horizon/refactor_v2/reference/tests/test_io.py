from pyledger.core.entry import Entry
from pyledger.core.ledger import new_ledger, record
from pyledger.ledger_io.csv_io import read_entries_csv, write_entries_csv
from pyledger.ledger_io.json_store import save_ledger, load_ledger


def sample_entries():
    return [
        Entry(entry_id="E1", date="2026-01-05", account="cash", amount=50000, kind="debit", memo="seed"),
        Entry(entry_id="E2", date="2026-01-05", account="owners_equity", amount=50000, kind="credit", memo="seed"),
    ]


def test_csv_round_trip(tmp_path):
    path = tmp_path / "entries.csv"
    write_entries_csv(path, sample_entries())
    loaded = read_entries_csv(path)
    assert [e.entry_id for e in loaded] == ["E1", "E2"]
    assert loaded[0].amount == 50000
    assert loaded[1].kind == "credit"


def test_json_round_trip(tmp_path):
    ledger = new_ledger("books")
    for e in sample_entries():
        record(ledger, e)
    path = tmp_path / "ledger.json"
    save_ledger(ledger, path)
    loaded = load_ledger(path)
    assert loaded["name"] == "books"
    assert loaded["entries"] == ledger["entries"]
