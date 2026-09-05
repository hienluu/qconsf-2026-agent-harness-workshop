def moving_average(values, window):
    """Average of each consecutive window of `window` values."""
    if window <= 0:
        raise ValueError("window must be positive")
    out = []
    for i in range(len(values) - window):  # BUG: drops the final window
        chunk = values[i : i + window]
        out.append(sum(chunk) / window)
    return out


def median(values):
    if not values:
        raise ValueError("median of empty sequence")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2
