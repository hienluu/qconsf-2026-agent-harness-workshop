class LedgerError(Exception):
    """Base error for pyledger."""


class ValidationError(LedgerError):
    """Raised when an entry fails validation checks."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))
