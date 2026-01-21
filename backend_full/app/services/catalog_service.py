from sqlalchemy.orm import Session
from app.models.models import Product, PriceList, Stock


class CatalogService:
    """Builds catalog views for locations."""

    def __init__(self, db: Session):
        self.db = db

    def catalog_for_location(self, location_id: int) -> list[dict]:
        products = self.db.query(Product).filter(Product.is_active == True).all()  # noqa: E712
        prices = {
            (p.product_id, p.unit_code): p
            for p in self.db.query(PriceList).filter(PriceList.location_id == location_id).all()
        }
        stocks = {s.product_id: s for s in self.db.query(Stock).filter(Stock.location_id == location_id).all()}
        items = []
        for product in products:
            price_entry = prices.get((product.id, product.base_unit_code))
            stock_entry = stocks.get(product.id)
            items.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "price": float(price_entry.amount) if price_entry else None,
                    "currency": price_entry.currency if price_entry else None,
                    "stock": float(stock_entry.quantity) if stock_entry else 0,
                    "unit": product.base_unit_code,
                    "category": product.primary_category,
                }
            )
        return items
