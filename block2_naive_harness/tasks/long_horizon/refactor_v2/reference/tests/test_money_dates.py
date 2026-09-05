from pyledger.utils.dates import is_iso_date, month_key, year_of
from pyledger.utils.money import to_cents, from_cents, format_amount


def test_to_cents_parses_decimals():
    assert to_cents("12.34") == 1234
    assert to_cents("0.5") == 50
    assert to_cents("1,000.00") == 100000
    assert to_cents("-3.07") == -307
    assert to_cents("7") == 700


def test_from_cents_renders_decimals():
    assert from_cents(1234) == "12.34"
    assert from_cents(-307) == "-3.07"
    assert from_cents(5) == "0.05"


def test_round_trip():
    for text in ("0.01", "99.99", "12000.00"):
        assert from_cents(to_cents(text)) == text


def test_format_amount_includes_currency():
    assert format_amount(1234) == "USD 12.34"
    assert format_amount(1234, "EUR") == "EUR 12.34"


def test_date_helpers():
    assert is_iso_date("2026-03-15")
    assert not is_iso_date("2026-13-01")
    assert not is_iso_date("15-03-2026")
    assert month_key("2026-03-15") == "2026-03"
    assert year_of("2026-03-15") == 2026
