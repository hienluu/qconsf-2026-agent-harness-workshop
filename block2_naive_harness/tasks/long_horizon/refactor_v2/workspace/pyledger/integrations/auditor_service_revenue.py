"""Audit pass for the service_revenue account."""

from pyledger.core.ledger import entries_by_account
from pyledger.core.validation import check_entry
from pyledger.errors import ValidationError

ACCOUNT = "service_revenue"


def audit_service_revenue(ledger) -> dict:
    clean, flagged = 0, []
    for e in entries_by_account(ledger, ACCOUNT):
        try:
            check_entry(e)
            clean += 1
        except ValidationError as err:
            flagged.append((e.entry_id, err.problems))
    return {"account": ACCOUNT, "clean": clean, "flagged": flagged}
