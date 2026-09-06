from ordercalc import Cart, LineItem


def test_line_item_total():
    assert LineItem("widget", 499, 3).total_cents() == 1497


def test_cart_subtotal_and_count():
    cart = Cart([LineItem("widget", 499, 3), LineItem("gadget", 250, 8)])
    assert cart.subtotal_cents() == 3497
    assert cart.item_count() == 11
