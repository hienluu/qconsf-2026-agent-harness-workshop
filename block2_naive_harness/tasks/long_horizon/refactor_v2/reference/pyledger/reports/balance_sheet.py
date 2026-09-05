from pyledger.core.accounts import accounts_of_type
from pyledger.core.ledger import get_balance


def balance_sheet(ledger: dict) -> dict:
    """Assets, liabilities, and equity totals in cents.

    Liability and equity accounts normally carry credit balances, so their
    signed totals are negated to present as positive numbers.
    """
    assets = sum(get_balance(ledger, a) for a in accounts_of_type("asset"))
    liabilities = -sum(get_balance(ledger, a) for a in accounts_of_type("liability"))
    equity = -sum(get_balance(ledger, a) for a in accounts_of_type("equity"))
    return {"assets": assets, "liabilities": liabilities, "equity": equity}
