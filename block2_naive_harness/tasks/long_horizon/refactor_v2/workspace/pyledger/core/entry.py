from dataclasses import dataclass, field


@dataclass
class Entry:
    """A single ledger line.

    Monetary values are stored as integer cents to avoid float drift.
    ``side`` is either ``"debit"`` or ``"credit"``.
    """

    entry_id: str
    date: str
    account: str
    amt: int
    side: str
    memo: str = ""
    tags: list = field(default_factory=list)

    def signed(self) -> int:
        """Return the value with debit positive and credit negative."""
        if self.side == "debit":
            return self.amt
        return -self.amt
