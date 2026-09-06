from ordercalc import Cart, LineItem, price_cart


def big_cart():
    return Cart([LineItem("widget", 499, 3), LineItem("gadget", 250, 8)])


def test_priced_cart_with_coupon():
    assert price_cart(big_cart(), coupon="SAVE5") == {
        "subtotal": 3497,
        "discount": 525,
        "tax": 238,
        "total": 3210,
    }


def test_big_cart_no_coupon():
    priced = price_cart(big_cart())
    assert priced["tax"] == 252
    assert priced["total"] == 3399


def test_small_cart_no_discounts():
    priced = price_cart(Cart([LineItem("pen", 150, 2)]))
    assert priced == {"subtotal": 300, "discount": 0, "tax": 24, "total": 324}


def test_empty_cart_totals_zero():
    assert price_cart(Cart()) == {"subtotal": 0, "discount": 0, "tax": 0, "total": 0}
