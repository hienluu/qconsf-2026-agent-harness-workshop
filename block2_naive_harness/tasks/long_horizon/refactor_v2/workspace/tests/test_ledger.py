import pytest

from pyledger import Entry, ValidationError, new_ledger, record, get_balance, entries_for


def make(id_, account, amount, kind, date="2026-01-15"):
    return Entry(entry_id=id_, date=date, account=account, amount=amount, kind=kind)


def test_new_ledger_is_empty():
    ledger = new_ledger("books")
    assert ledger["name"] == "books"
    assert ledger["entries"] == []


def test_record_appends_valid_entry():
    ledger = new_ledger("books")
    record(ledger, make("E1", "cash", 5000, "debit"))
    assert len(ledger["entries"]) == 1


def test_record_rejects_invalid_entry():
    ledger = new_ledger("books")
    with pytest.raises(ValidationError):
        record(ledger, make("E1", "not_an_account", 5000, "debit"))
    assert ledger["entries"] == []


def test_get_balance_nets_debits_and_credits():
    ledger = new_ledger("books")
    record(ledger, make("E1", "cash", 10000, "debit"))
    record(ledger, make("E2", "cash", 2500, "credit"))
    assert get_balance(ledger, "cash") == 7500


def test_get_balance_unknown_account_is_zero():
    assert get_balance(new_ledger("books"), "cash") == 0


def test_entries_for_filters_by_account():
    ledger = new_ledger("books")
    record(ledger, make("E1", "cash", 100, "debit"))
    record(ledger, make("E2", "inventory", 200, "debit"))
    record(ledger, make("E3", "cash", 50, "credit"))
    assert [e.entry_id for e in entries_for(ledger, "cash")] == ["E1", "E3"]
