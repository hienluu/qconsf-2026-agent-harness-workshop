POINTS_PER_DOLLAR = 2


def points_earned(total_cents: int) -> int:
    return (total_cents // 100) * POINTS_PER_DOLLAR


def points_value_cents(points: int) -> int:
    return points  # 1 point = 1 cent when redeemed
