from pyledger.core.accounts import accounts_of_type
from pyledger.core.ledger import get_balance


def income_statement(ledger: dict) -> dict:
    """Revenue, expenses, and net income in cents.

    Revenue accounts carry credit balances, so signed totals are negated.
    """
    revenue = -sum(get_balance(ledger, a) for a in accounts_of_type("revenue"))
    expenses = sum(get_balance(ledger, a) for a in accounts_of_type("expense"))
    return {"revenue": revenue, "expenses": expenses, "net_income": revenue - expenses}
