from pyledger.core.accounts import accounts_of_type
from pyledger.core.ledger import balance_of


def income_statement(ledger: dict) -> dict:
    """Revenue, expenses, and net income in cents.

    Revenue accounts carry credit balances, so signed totals are negated.
    """
    revenue = -sum(balance_of(ledger, a) for a in accounts_of_type("revenue"))
    expenses = sum(balance_of(ledger, a) for a in accounts_of_type("expense"))
    return {"revenue": revenue, "expenses": expenses, "net_income": revenue - expenses}
