"""In-memory repository so use-case tests need no database."""

import dataclasses
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from application.catalog.interfaces import ProductRepository
from domain.catalog.entities import Product


class FakeProductRepository(ProductRepository):
    def __init__(self, products: Sequence[Product] = ()):
        self._rows: dict[int, Product] = {}
        self._next_id = 1
        for product in products:
            self.add(product)

    def list_active(self) -> Sequence[Product]:
        active = [p for p in self._rows.values() if p.is_active]
        return sorted(active, key=lambda p: p.created_at, reverse=True)

    def get_active(self, product_id: int) -> Product | None:
        product = self._rows.get(product_id)
        return product if product is not None and product.is_active else None

    def get(self, product_id: int) -> Product | None:
        return self._rows.get(product_id)

    def add(self, product: Product) -> Product:
        stored = dataclasses.replace(
            product,
            id=self._next_id,
            # Strictly increasing, so ordering assertions are deterministic.
            created_at=datetime.now(UTC) + timedelta(microseconds=self._next_id),
        )
        self._rows[self._next_id] = stored
        self._next_id += 1
        return stored

    def update(self, product: Product) -> Product:
        self._rows[product.id] = product
        return product

    def delete(self, product_id: int) -> None:
        self._rows.pop(product_id, None)

    def count(self) -> int:
        """Test-only convenience."""
        return len(self._rows)
