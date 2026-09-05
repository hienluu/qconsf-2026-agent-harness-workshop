from pyledger.core.entry import Entry
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
    assert len(registry.ALL_EXPORTERS) == 14


def test_sampled_variants_work():
    ledger = seeded()
    from pyledger.integrations.auditor_cash import audit_cash
    from pyledger.integrations.reconciler_cash import reconcile_cash
    from pyledger.integrations.snapshot_sales_revenue import snapshot_sales_revenue
    from pyledger.integrations.limits_owners_equity import within_limit_owners_equity
    from pyledger.integrations.history_cash import history_cash

    assert audit_cash(ledger)["clean"] == 2
    assert reconcile_cash(ledger, "800.00")["delta"] == 0
    assert snapshot_sales_revenue(ledger)["net"] == "-300.00"
    assert within_limit_owners_equity(ledger)
    assert history_cash(ledger) == [("2026-01", "debit", 50000), ("2026-02", "debit", 30000)]


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
