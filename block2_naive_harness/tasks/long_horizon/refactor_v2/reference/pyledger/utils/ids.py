import itertools

_counter = itertools.count(1)


def next_entry_id(prefix: str = "E") -> str:
    return f"{prefix}{next(_counter):06d}"


def reset_ids() -> None:
    """Restart the sequence; used by tests for determinism."""
    global _counter
    _counter = itertools.count(1)
