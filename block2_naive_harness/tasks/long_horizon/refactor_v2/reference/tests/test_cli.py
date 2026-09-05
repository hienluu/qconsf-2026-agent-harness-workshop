import cli
from pyledger.ledger_io.csv_io import write_entries_csv
from pyledger.core.entry import Entry


def test_cli_prints_summary_and_balance(tmp_path, capsys):
    path = tmp_path / "entries.csv"
    write_entries_csv(
        path,
        [
            Entry(entry_id="E1", date="2026-01-05", account="cash", amount=1000, kind="debit"),
            Entry(entry_id="E2", date="2026-01-05", account="sales_revenue", amount=1000, kind="credit"),
        ],
    )
    assert cli.main([str(path), "--name", "demo"]) == 0
    out = capsys.readouterr().out
    assert "Ledger: demo" in out
    assert "balanced" in out
