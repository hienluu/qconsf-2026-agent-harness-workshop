import re

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_iso_date(text: str) -> bool:
    if not isinstance(text, str) or not _ISO.match(text):
        return False
    month = int(text[5:7])
    day = int(text[8:10])
    return 1 <= month <= 12 and 1 <= day <= 31


def month_key(date: str) -> str:
    """'2026-03-15' -> '2026-03'."""
    return date[:7]


def year_of(date: str) -> int:
    return int(date[:4])
