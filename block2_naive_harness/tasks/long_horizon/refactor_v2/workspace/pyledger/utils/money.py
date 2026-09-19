def to_cents(dollars: str) -> int:
    """Parse a decimal string like '12.34' into integer cents."""
    text = dollars.strip().replace(",", "")
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    if "." in text:
        whole, frac = text.split(".", 1)
        frac = (frac + "00")[:2]
    else:
        whole, frac = text, "00"
    value = int(whole or "0") * 100 + int(frac)
    return -value if negative else value


def from_cents(cents: int) -> str:
    """Render integer cents as a decimal string like '12.34'."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def format_amount(cents: int, currency: str = "USD") -> str:
    """Human-readable rendering, e.g. 'USD 12.34'."""
    return f"{currency} {from_cents(cents)}"
