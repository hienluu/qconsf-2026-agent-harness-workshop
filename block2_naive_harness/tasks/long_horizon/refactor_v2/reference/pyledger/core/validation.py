from pyledger.core.accounts import is_valid_account
from pyledger.errors import ValidationError
from pyledger.utils.dates import is_iso_date


def validate_entry(entry) -> None:
    """Raise ValidationError listing every problem found; return None if clean."""
    problems = []
    if not entry.entry_id:
        problems.append("entry_id is required")
    if not is_iso_date(entry.date):
        problems.append(f"date {entry.date!r} is not YYYY-MM-DD")
    if not is_valid_account(entry.account):
        problems.append(f"unknown account {entry.account!r}")
    if not isinstance(entry.amount, int) or entry.amount <= 0:
        problems.append("value must be a positive integer of cents")
    if entry.kind not in ("debit", "credit"):
        problems.append(f"expected debit or credit, got {entry.kind!r}")
    if problems:
        raise ValidationError(problems)
