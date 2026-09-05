"""Audit pass for the owners_equity account."""

from pyledger.core.ledger import entries_for
from pyledger.core.validation import validate_entry
from pyledger.errors import ValidationError

ACCOUNT = "owners_equity"


def audit_owners_equity(ledger) -> dict:
    clean, flagged = 0, []
    for e in entries_for(ledger, ACCOUNT):
        try:
            validate_entry(e)
            clean += 1
        except ValidationError as err:
            flagged.append((e.entry_id, err.problems))
    return {"account": ACCOUNT, "clean": clean, "flagged": flagged}
