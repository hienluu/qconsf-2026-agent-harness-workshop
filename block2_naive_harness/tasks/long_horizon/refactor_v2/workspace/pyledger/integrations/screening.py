"""Entry screening hooks run before bulk loads."""

from pyledger.core.validation import check_entry
from pyledger.errors import ValidationError


def screen(entries) -> dict:
    good, bad = [], []
    for entry in entries:
        try:
            check_entry(entry)
            good.append(entry)
        except ValidationError as err:
            bad.append((entry, err.problems))
    return {"accepted": good, "rejected": bad}
