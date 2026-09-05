CHART = {
    "cash": "asset",
    "accounts_receivable": "asset",
    "inventory": "asset",
    "equipment": "asset",
    "accounts_payable": "liability",
    "loans_payable": "liability",
    "owners_equity": "equity",
    "retained_earnings": "equity",
    "sales_revenue": "revenue",
    "service_revenue": "revenue",
    "cost_of_goods": "expense",
    "rent_expense": "expense",
    "salaries_expense": "expense",
    "utilities_expense": "expense",
}


def is_valid_account(account: str) -> bool:
    return account in CHART


def account_type(account: str) -> str:
    return CHART[account]


def accounts_of_type(type_name: str) -> list:
    return sorted(a for a, t in CHART.items() if t == type_name)
