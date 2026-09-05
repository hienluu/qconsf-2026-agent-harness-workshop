"""Ledger health checks used by the nightly job."""

from pyledger.reports.trial_balance import trial_balance, balanced


def health_report(ledger) -> dict:
    return {
        "balanced": balanced(ledger),
        "active_accounts": len(trial_balance(ledger)),
        "entry_count": len(ledger["entries"]),
    }
