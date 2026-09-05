from pyledger.utils.dates import month_key
from pyledger.utils.money import format_amount


def monthly_summary(ledger: dict) -> dict:
    """Map of 'YYYY-MM' -> {'debits': cents, 'credits': cents}."""
    out = {}
    for e in ledger["entries"]:
        bucket = out.setdefault(month_key(e.date), {"debits": 0, "credits": 0})
        if e.kind == "debit":
            bucket["debits"] += e.amount
        else:
            bucket["credits"] += e.amount
    return out


def render_summary(ledger: dict) -> str:
    lines = [f"Ledger: {ledger['name']}"]
    for month, totals in sorted(monthly_summary(ledger).items()):
        lines.append(
            f"  {month}  debits {format_amount(totals['debits'])}"
            f"  credits {format_amount(totals['credits'])}"
        )
    return "\n".join(lines)
