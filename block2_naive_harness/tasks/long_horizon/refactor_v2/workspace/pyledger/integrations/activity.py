"""Cross-account activity analysis."""

from pyledger.reports.summary import summary_by_month
from pyledger.utils.money import from_minor


def busiest_month(ledger) -> str:
    months = summary_by_month(ledger)
    if not months:
        return "no activity"
    month = max(months, key=lambda m: months[m]["debits"] + months[m]["credits"])
    volume = months[month]["debits"] + months[month]["credits"]
    return f"{month} ({from_minor(volume)})"
