import pytest

from pyledger.core.entry import Entry
from pyledger.core.validation import validate_entry
from pyledger.errors import ValidationError


def good():
    return Entry(entry_id="E1", date="2026-02-01", account="cash", amount=100, kind="debit")


def test_valid_entry_passes():
    validate_entry(good())


def test_signed_flips_for_credit():
    e = good()
    assert e.signed() == 100
    e.kind = "credit"
    assert e.signed() == -100


def test_bad_date_reported():
    e = good()
    e.date = "02/01/2026"
    with pytest.raises(ValidationError) as err:
        validate_entry(e)
    assert any("date" in p for p in err.value.problems)


def test_nonpositive_amount_reported():
    e = good()
    e.amount = 0
    with pytest.raises(ValidationError):
        validate_entry(e)


def test_bad_kind_reported():
    e = good()
    e.kind = "withdrawal"
    with pytest.raises(ValidationError) as err:
        validate_entry(e)
    assert any("debit or credit" in p for p in err.value.problems)


def test_multiple_problems_collected():
    e = Entry(entry_id="", date="nope", account="cash", amount=-5, kind="debit")
    with pytest.raises(ValidationError) as err:
        validate_entry(e)
    assert len(err.value.problems) == 3
