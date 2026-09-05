from pyledger.core.entry import Entry
from pyledger.core.ledger import new_ledger, record
from pyledger.reports.balance_sheet import balance_sheet
from pyledger.reports.income_statement import income_statement
from pyledger.reports.summary import monthly_summary, render_summary
from pyledger.reports.trial_balance import trial_balance, is_balanced, full_trial_balance


def seeded_ledger():
    ledger = new_ledger("books")
    rows = [
        ("E1", "2026-01-05", "cash", 50000, "debit"),
        ("E2", "2026-01-05", "owners_equity", 50000, "credit"),
        ("E3", "2026-01-20", "rent_expense", 12000, "debit"),
        ("E4", "2026-01-20", "cash", 12000, "credit"),
        ("E5", "2026-02-02", "cash", 30000, "debit"),
        ("E6", "2026-02-02", "sales_revenue", 30000, "credit"),
    ]
    for id_, date, account, amount, kind in rows:
        record(ledger, Entry(entry_id=id_, date=date, account=account, amount=amount, kind=kind))
    return ledger


def test_trial_balance_only_active_accounts():
    tb = trial_balance(seeded_ledger())
    assert tb["cash"] == 68000
    assert tb["owners_equity"] == -50000
    assert "inventory" not in tb


def test_full_trial_balance_covers_chart():
    tb = full_trial_balance(seeded_ledger())
    assert tb["inventory"] == 0
    assert len(tb) == 14


def test_ledger_is_balanced():
    assert is_balanced(seeded_ledger())


def test_balance_sheet_totals():
    bs = balance_sheet(seeded_ledger())
    assert bs["assets"] == 68000
    assert bs["equity"] == 50000


def test_income_statement_totals():
    inc = income_statement(seeded_ledger())
    assert inc == {"revenue": 30000, "expenses": 12000, "net_income": 18000}


def test_monthly_summary_buckets():
    ms = monthly_summary(seeded_ledger())
    assert ms["2026-01"] == {"debits": 62000, "credits": 62000}
    assert ms["2026-02"] == {"debits": 30000, "credits": 30000}


def test_render_summary_mentions_ledger_name():
    assert render_summary(seeded_ledger()).startswith("Ledger: books")
