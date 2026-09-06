def money(cents: int) -> str:
    return f"${cents // 100}.{cents % 100:02d}"


def format_receipt(cart, pricing: dict) -> str:
    count = cart.item_count()
    lines = [f"ITEMS: {count}"]
    for item in cart.items:
        lines.append(f"  {item.name} x{item.quantity} {money(item.total_cents())}")
    average = cart.subtotal_cents() // count if count else 0
    lines.append(f"AVG PER ITEM: {money(average)}")
    lines.append(f"SUBTOTAL: {money(pricing['subtotal'])}")
    lines.append(f"DISCOUNT: -{money(pricing['discount'])}")
    lines.append(f"TAX: {money(pricing['tax'])}")
    lines.append(f"TOTAL: {money(pricing['total'])}")
    return "\n".join(lines)
