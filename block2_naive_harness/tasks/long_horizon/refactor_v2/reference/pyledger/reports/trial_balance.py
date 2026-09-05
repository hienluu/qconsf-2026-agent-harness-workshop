from pyledger.core.accounts import CHART
from pyledger.core.ledger import get_balance


def trial_balance(ledger: dict) -> dict:
    """Map of account -> net cents, for every account with activity."""
    seen = {e.account for e in ledger["entries"]}
    return {a: get_balance(ledger, a) for a in sorted(seen)}


def is_balanced(ledger: dict) -> bool:
    """Debits equal credits across the whole ledger."""
    return sum(e.signed() for e in ledger["entries"]) == 0


def full_trial_balance(ledger: dict) -> dict:
    """Every account in the chart, active or not."""
    return {a: get_balance(ledger, a) for a in sorted(CHART)}
