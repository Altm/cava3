from app.services.promo_service import PromoEngine, CartLine


def test_buy_two_get_one_applies():
    engine = PromoEngine()
    cart = [CartLine(product_id=1, qty=2, unit="bottle")]
    result = engine.apply_buy_x_get_y(cart, buy_product=1, buy_qty=2, free_product=2, free_qty=1)
    assert result["applied"] is True
    assert any(line.product_id == 2 for line in cart)
