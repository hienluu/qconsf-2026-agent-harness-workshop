"""Statement bundle assembled for month-end close."""

from pyledger.reports.balance_sheet import balance_sheet
from pyledger.reports.income_statement import income_statement
from pyledger.utils.money import to_minor


def month_end_bundle(ledger, materiality: str = "0.00") -> dict:
    floor = to_minor(materiality)
    inc = income_statement(ledger)
    return {
        "balance_sheet": balance_sheet(ledger),
        "income_statement": inc,
        "material": abs(inc["net_income"]) >= floor,
    }
