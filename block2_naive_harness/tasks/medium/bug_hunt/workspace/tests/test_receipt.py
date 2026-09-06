from ordercalc import Cart, LineItem, price_cart
from ordercalc.receipt import format_receipt, money


def test_money_formatting():
    assert money(3210) == "$32.10"
    assert money(5) == "$0.05"


def test_receipt_lists_items_and_average():
    cart = Cart([LineItem("widget", 499, 3), LineItem("gadget", 250, 8)])
    text = format_receipt(cart, price_cart(cart))
    assert "widget x3 $14.97" in text
    assert "AVG PER ITEM: $3.17" in text  # 3497 // 11 = 317
    assert "TOTAL:" in text


def test_empty_cart_receipt():
    text = format_receipt(Cart(), price_cart(Cart()))
    assert "ITEMS: 0" in text
    assert "AVG PER ITEM: $0.00" in text
