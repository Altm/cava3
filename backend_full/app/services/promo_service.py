from dataclasses import dataclass
from typing import List


@dataclass
class CartLine:
    product_id: int
    qty: int
    unit: str


class PromoEngine:
    """Simple buy X get Y engine."""

    def apply_buy_x_get_y(self, cart: List[CartLine], buy_product: int, buy_qty: int, free_product: int, free_qty: int):
        for line in cart:
            if line.product_id == buy_product and line.qty >= buy_qty:
                cart.append(CartLine(product_id=free_product, qty=free_qty, unit=line.unit))
                return {"applied": True, "free_items": [{"product_id": free_product, "qty": free_qty}]}
        return {"applied": False, "free_items": []}
