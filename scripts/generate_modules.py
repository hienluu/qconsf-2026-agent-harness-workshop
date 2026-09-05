"""Generate the integrations layer of the v2 reference codebase.

Emits one exporter module per chart account plus a handful of analyzers,
a registry that imports every module (serially — so in the derived v1
workspace, unmigrated modules surface one ImportError at a time), and a
webhook stub whose post() is an HTTP verb, NOT the ledger API (the
find-and-replace trap).

Run once, commit the output. Re-run after changing templates, then re-run
derive_workspace.py.

Usage: python scripts/generate_modules.py
"""

from pathlib import Path

REFERENCE = Path(__file__).resolve().parent.parent / "block2_naive_harness" / "tasks" / "long_horizon" / "refactor_v2" / "reference"
PKG = REFERENCE / "pyledger" / "integrations"

ACCOUNTS = [
    "cash", "accounts_receivable", "inventory", "equipment",
    "accounts_payable", "loans_payable", "owners_equity", "retained_earnings",
    "sales_revenue", "service_revenue", "cost_of_goods", "rent_expense",
    "salaries_expense", "utilities_expense",
]

EXPORTER = '''"""Exporter for the {account} account."""

from pyledger.core.ledger import get_balance, entries_for
from pyledger.utils.money import format_amount

ACCOUNT = "{account}"


def export_{account}(ledger) -> str:
    lines = [f"{{ACCOUNT}}: {{format_amount(get_balance(ledger, ACCOUNT))}}"]
    for e in entries_for(ledger, ACCOUNT):
        lines.append(f"  {{e.entry_id}} {{e.date}} {{e.kind}} {{format_amount(e.amount)}}")
    return "\\n".join(lines)


def debit_total_{account}(ledger) -> int:
    return sum(e.amount for e in entries_for(ledger, ACCOUNT) if e.kind == "debit")


def credit_total_{account}(ledger) -> int:
    return sum(e.amount for e in entries_for(ledger, ACCOUNT) if e.kind == "credit")
'''

ANALYZERS = {
    "activity": '''"""Cross-account activity analysis."""

from pyledger.reports.summary import monthly_summary
from pyledger.utils.money import from_cents


def busiest_month(ledger) -> str:
    months = monthly_summary(ledger)
    if not months:
        return "no activity"
    month = max(months, key=lambda m: months[m]["debits"] + months[m]["credits"])
    volume = months[month]["debits"] + months[month]["credits"]
    return f"{month} ({from_cents(volume)})"
''',
    "health": '''"""Ledger health checks used by the nightly job."""

from pyledger.reports.trial_balance import trial_balance, is_balanced


def health_report(ledger) -> dict:
    return {
        "is_balanced": is_balanced(ledger),
        "active_accounts": len(trial_balance(ledger)),
        "entry_count": len(ledger["entries"]),
    }
''',
    "importer": '''"""Bulk import: CSV files straight into a fresh ledger."""

from pyledger.core.ledger import new_ledger, record
from pyledger.ledger_io.csv_io import read_entries_csv


def import_csv(name: str, path):
    ledger = new_ledger(name)
    for entry in read_entries_csv(path):
        record(ledger, entry)
    return ledger
''',
    "exporter_csv": '''"""Bulk export: one account's entries to a CSV file."""

from pyledger.core.ledger import entries_for
from pyledger.ledger_io.csv_io import write_entries_csv


def export_account_csv(ledger, account: str, path) -> int:
    entries = entries_for(ledger, account)
    write_entries_csv(path, entries)
    return len(entries)
''',
    "screening": '''"""Entry screening hooks run before bulk loads."""

from pyledger.core.validation import validate_entry
from pyledger.errors import ValidationError


def screen(entries) -> dict:
    good, bad = [], []
    for entry in entries:
        try:
            validate_entry(entry)
            good.append(entry)
        except ValidationError as err:
            bad.append((entry, err.problems))
    return {"accepted": good, "rejected": bad}
''',
    "statements": '''"""Statement bundle assembled for month-end close."""

from pyledger.reports.balance_sheet import balance_sheet
from pyledger.reports.income_statement import income_statement
from pyledger.utils.money import to_cents


def month_end_bundle(ledger, materiality: str = "0.00") -> dict:
    floor = to_cents(materiality)
    inc = income_statement(ledger)
    return {
        "balance_sheet": balance_sheet(ledger),
        "income_statement": inc,
        "material": abs(inc["net_income"]) >= floor,
    }
''',
}

WEBHOOK = '''"""Outbound HTTP notifications (stub — no real network).

NOTE: post() here is the HTTP verb. It is NOT part of the ledger API and
is NOT covered by the v2 migration.
"""

SENT = []


def post(url: str, payload: dict) -> dict:
    SENT.append((url, payload))
    return {"status": 202, "url": url}


def ping(url: str) -> dict:
    return post(url, {"event": "ping"})
'''

TEST = '''from pyledger.core.entry import Entry
from pyledger.core.ledger import new_ledger, record
from pyledger.integrations import registry
from pyledger.integrations.activity import busiest_month
from pyledger.integrations.exporter_cash import export_cash, debit_total_cash
from pyledger.integrations.health import health_report
from pyledger.integrations.importer import import_csv
from pyledger.integrations.exporter_csv import export_account_csv
from pyledger.integrations.screening import screen
from pyledger.integrations.statements import month_end_bundle
from pyledger.integrations.webhook import post, ping


def seeded():
    ledger = new_ledger("books")
    rows = [
        ("E1", "2026-01-05", "cash", 50000, "debit"),
        ("E2", "2026-01-05", "owners_equity", 50000, "credit"),
        ("E3", "2026-02-02", "cash", 30000, "debit"),
        ("E4", "2026-02-02", "sales_revenue", 30000, "credit"),
    ]
    for id_, date, account, amount, kind in rows:
        record(ledger, Entry(entry_id=id_, date=date, account=account, amount=amount, kind=kind))
    return ledger


def test_registry_imports_every_exporter():
    assert len(registry.ALL_EXPORTERS) == {n_accounts}


def test_cash_exporter():
    ledger = seeded()
    assert "cash: USD 800.00" in export_cash(ledger)
    assert debit_total_cash(ledger) == 80000


def test_activity_and_health():
    ledger = seeded()
    assert busiest_month(ledger) == "2026-01 (1000.00)"
    report = health_report(ledger)
    assert report["is_balanced"] and report["active_accounts"] == 3


def test_csv_import_export_round_trip(tmp_path):
    ledger = seeded()
    path = tmp_path / "cash.csv"
    assert export_account_csv(ledger, "cash", path) == 2
    imported = import_csv("copy", path)
    assert len(imported["entries"]) == 2


def test_screening_partitions():
    ledger = seeded()
    bad = Entry(entry_id="", date="nope", account="cash", amount=-1, kind="debit")
    result = screen(ledger["entries"] + [bad])
    assert len(result["accepted"]) == 4 and len(result["rejected"]) == 1


def test_month_end_bundle():
    bundle = month_end_bundle(seeded(), materiality="100.00")
    assert bundle["income_statement"]["net_income"] == 30000
    assert bundle["material"]


def test_webhook_post_is_not_ledger_api():
    # post() is the HTTP verb and must keep its name through the migration.
    assert post("https://example.test/hook", {"a": 1})["status"] == 202
    assert ping("https://example.test/hook")["url"] == "https://example.test/hook"
'''


def main() -> None:
    PKG.mkdir(parents=True, exist_ok=True)
    (PKG / "__init__.py").write_text("")

    names = []
    for account in ACCOUNTS:
        name = f"exporter_{account}"
        (PKG / f"{name}.py").write_text(EXPORTER.format(account=account))
        names.append(name)
    for name, body in ANALYZERS.items():
        (PKG / f"{name}.py").write_text(body)
        names.append(name)
    (PKG / "webhook.py").write_text(WEBHOOK)
    names.append("webhook")

    imports = "\n".join(f"from pyledger.integrations import {n}" for n in sorted(names))
    exporters = ",\n    ".join(f"{n}" for n in sorted(names) if n.startswith("exporter_") and n != "exporter_csv")
    (PKG / "registry.py").write_text(
        '"""Imports every integration; any broken module breaks the registry."""\n\n'
        + imports
        + "\n\nALL_EXPORTERS = [\n    " + exporters + ",\n]\n"
    )

    (REFERENCE / "tests" / "test_integrations.py").write_text(
        TEST.replace("{n_accounts}", str(len(ACCOUNTS)))
    )
    print(f"generated {len(names)} integration modules + registry + tests")


if __name__ == "__main__":
    main()
