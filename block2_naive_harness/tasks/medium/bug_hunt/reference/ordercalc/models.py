from dataclasses import dataclass, field


@dataclass
class LineItem:
    name: str
    unit_cents: int
    quantity: int

    def total_cents(self) -> int:
        return self.unit_cents * self.quantity


@dataclass
class Cart:
    items: list = field(default_factory=list)

    def subtotal_cents(self) -> int:
        return sum(item.total_cents() for item in self.items)

    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)
