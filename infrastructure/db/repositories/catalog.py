from collections.abc import Sequence

from application.catalog.interfaces import ProductRepository
from domain.catalog.entities import Product
from infrastructure.db.models import ProductModel


class DjangoProductRepository(ProductRepository):
    """The only module in the catalog permitted to touch the ORM."""

    def list_active(self) -> Sequence[Product]:
        rows = ProductModel.objects.filter(is_active=True)
        return [self._to_entity(row) for row in rows]

    def get_active(self, product_id: int) -> Product | None:
        row = ProductModel.objects.filter(pk=product_id, is_active=True).first()
        return self._to_entity(row) if row is not None else None

    def get(self, product_id: int) -> Product | None:
        row = ProductModel.objects.filter(pk=product_id).first()
        return self._to_entity(row) if row is not None else None

    def add(self, product: Product) -> Product:
        row = ProductModel.objects.create(**self._to_columns(product))
        return self._to_entity(row)

    def update(self, product: Product) -> Product:
        ProductModel.objects.filter(pk=product.id).update(**self._to_columns(product))
        return self.get(product.id)

    def delete(self, product_id: int) -> None:
        ProductModel.objects.filter(pk=product_id).delete()

    @staticmethod
    def _to_columns(product: Product) -> dict:
        return {
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "image_url": product.image_url,
            "is_active": product.is_active,
        }

    @staticmethod
    def _to_entity(row: ProductModel) -> Product:
        return Product(
            id=row.pk,
            name=row.name,
            description=row.description,
            price=row.price,
            stock=row.stock,
            image_url=row.image_url,
            is_active=row.is_active,
            created_at=row.created_at,
        )
