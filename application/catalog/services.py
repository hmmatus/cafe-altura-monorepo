import dataclasses
from collections.abc import Sequence

from application.catalog.dtos import ProductDraft
from application.catalog.interfaces import ProductRepository
from domain.catalog.entities import Product
from domain.catalog.exceptions import ProductNotFound


class ListProducts:
    """The visitor-facing catalog: active products, newest first."""

    def __init__(self, products: ProductRepository):
        self._products = products

    def execute(self) -> Sequence[Product]:
        return self._products.list_active()


class GetProduct:
    """One product from the visitor-facing catalog. Inactive products read as absent."""

    def __init__(self, products: ProductRepository):
        self._products = products

    def execute(self, product_id: int) -> Product:
        product = self._products.get_active(product_id)
        if product is None:
            raise ProductNotFound("No existe ese producto.")

        return product


class CreateProduct:
    """Adds a product. Invariants are the entity's, so ProductInvalid propagates uncaught."""

    def __init__(self, products: ProductRepository):
        self._products = products

    def execute(self, draft: ProductDraft) -> Product:
        return self._products.add(Product(**draft.changes()))


class UpdateProduct:
    """Merges a partial draft onto a stored product, re-running every invariant."""

    def __init__(self, products: ProductRepository):
        self._products = products

    def execute(self, product_id: int, draft: ProductDraft) -> Product:
        stored = self._products.get(product_id)
        if stored is None:
            raise ProductNotFound("No existe ese producto.")

        # replace() re-runs __post_init__, so an update cannot bypass the invariants.
        return self._products.update(dataclasses.replace(stored, **draft.changes()))


class DeleteProduct:
    """Removes a product permanently. Deactivating is the reversible alternative."""

    def __init__(self, products: ProductRepository):
        self._products = products

    def execute(self, product_id: int) -> None:
        if self._products.get(product_id) is None:
            raise ProductNotFound("No existe ese producto.")

        self._products.delete(product_id)
