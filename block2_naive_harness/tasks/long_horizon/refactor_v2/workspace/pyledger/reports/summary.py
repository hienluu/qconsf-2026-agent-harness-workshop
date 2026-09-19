from pyledger.utils.dates import month_key
from pyledger.utils.money import fmt_amt


def summary_by_month(ledger: dict) -> dict:
    """Map of 'YYYY-MM' -> {'debits': cents, 'credits': cents}."""
    out = {}
    for e in ledger["entries"]:
        bucket = out.setdefault(month_key(e.date), {"debits": 0, "credits": 0})
        if e.side == "debit":
            bucket["debits"] += e.amt
        else:
            bucket["credits"] += e.amt
    return out


def render_summary(ledger: dict) -> str:
    lines = [f"Ledger: {ledger['name']}"]
    for month, totals in sorted(summary_by_month(ledger).items()):
        lines.append(
            f"  {month}  debits {fmt_amt(totals['debits'])}"
            f"  credits {fmt_amt(totals['credits'])}"
        )
    return "\n".join(lines)
