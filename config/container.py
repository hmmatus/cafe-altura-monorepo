"""Composition root.

The only module allowed to name concrete infrastructure classes. Everything else depends on
the abstract ports in `application/`.
"""

from application.catalog.services import (
    CreateProduct,
    DeleteProduct,
    GetProduct,
    ListProducts,
    UpdateProduct,
)
from application.health.services import CheckHealth
from infrastructure.db.probes import DatabaseProbe
from infrastructure.db.repositories.catalog import DjangoProductRepository


def check_health() -> CheckHealth:
    return CheckHealth(probes=[DatabaseProbe()])


def list_products() -> ListProducts:
    return ListProducts(products=DjangoProductRepository())


def get_product() -> GetProduct:
    return GetProduct(products=DjangoProductRepository())


def create_product() -> CreateProduct:
    return CreateProduct(products=DjangoProductRepository())


def update_product() -> UpdateProduct:
    return UpdateProduct(products=DjangoProductRepository())


def delete_product() -> DeleteProduct:
    return DeleteProduct(products=DjangoProductRepository())
