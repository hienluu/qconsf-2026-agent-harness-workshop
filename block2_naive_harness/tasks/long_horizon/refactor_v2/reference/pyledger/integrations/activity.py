"""Cross-account activity analysis."""

from pyledger.reports.summary import monthly_summary
from pyledger.utils.money import from_cents


def busiest_month(ledger) -> str:
    months = monthly_summary(ledger)
    if not months:
        return "no activity"
    month = max(months, key=lambda m: months[m]["debits"] + months[m]["credits"])
    volume = months[month]["debits"] + months[month]["credits"]
    return f"{month} ({from_cents(volume)})"
