"""Use-case tests: no database, no HTTP, no Django test case."""

import unittest
from decimal import Decimal

from application.catalog.dtos import ProductDraft
from application.catalog.services import (
    CreateProduct,
    DeleteProduct,
    GetProduct,
    ListProducts,
    UpdateProduct,
)
from domain.catalog.entities import Product
from domain.catalog.exceptions import ProductInvalid, ProductNotFound
from tests.application.catalog.fakes import FakeProductRepository


class ListProductsTests(unittest.TestCase):
    def test_returns_the_active_products_the_repository_holds(self):
        repo = FakeProductRepository(
            [
                Product(name="Primero", price=Decimal("1.00")),
                Product(name="Segundo", price=Decimal("2.00")),
            ]
        )

        products = ListProducts(products=repo).execute()

        self.assertEqual({"Primero", "Segundo"}, {p.name for p in products})

    def test_returns_empty_when_the_catalog_is_empty(self):
        self.assertEqual([], list(ListProducts(products=FakeProductRepository()).execute()))

    def test_omits_inactive_products(self):
        repo = FakeProductRepository(
            [
                Product(name="Visible", price=Decimal("1.00")),
                Product(name="Oculto", price=Decimal("1.00"), is_active=False),
            ]
        )

        self.assertEqual(["Visible"], [p.name for p in ListProducts(products=repo).execute()])


class GetProductTests(unittest.TestCase):
    def test_returns_the_product(self):
        repo = FakeProductRepository([Product(name="Espresso", price=Decimal("12.50"))])

        self.assertEqual("Espresso", GetProduct(products=repo).execute(1).name)

    def test_raises_when_the_product_is_absent(self):
        with self.assertRaises(ProductNotFound):
            GetProduct(products=FakeProductRepository()).execute(999)

    def test_raises_when_the_product_is_inactive(self):
        repo = FakeProductRepository(
            [Product(name="Oculto", price=Decimal("1.00"), is_active=False)]
        )

        with self.assertRaises(ProductNotFound):
            GetProduct(products=repo).execute(1)


class CreateProductTests(unittest.TestCase):
    def test_persists_a_valid_draft_and_returns_it_with_an_id(self):
        repo = FakeProductRepository()
        draft = ProductDraft.from_mapping({"name": "Espresso", "price": Decimal("12.50")})

        created = CreateProduct(products=repo).execute(draft)

        self.assertEqual(1, created.id)
        self.assertEqual(1, repo.count())

    def test_applies_defaults_for_fields_the_draft_omits(self):
        draft = ProductDraft.from_mapping({"name": "Espresso", "price": Decimal("12.50")})

        created = CreateProduct(products=FakeProductRepository()).execute(draft)

        self.assertEqual("", created.description)
        self.assertEqual(0, created.stock)
        self.assertEqual("", created.image_url)
        self.assertTrue(created.is_active)

    def test_a_zero_price_is_refused_and_nothing_is_stored(self):
        repo = FakeProductRepository()
        draft = ProductDraft.from_mapping({"name": "Gratis", "price": Decimal("0")})

        with self.assertRaises(ProductInvalid):
            CreateProduct(products=repo).execute(draft)

        self.assertEqual(0, repo.count())

    def test_a_negative_stock_is_refused_and_nothing_is_stored(self):
        repo = FakeProductRepository()
        draft = ProductDraft.from_mapping(
            {"name": "Negativo", "price": Decimal("1.00"), "stock": -1}
        )

        with self.assertRaises(ProductInvalid):
            CreateProduct(products=repo).execute(draft)

        self.assertEqual(0, repo.count())


class UpdateProductTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeProductRepository(
            [
                Product(
                    name="Espresso",
                    price=Decimal("12.50"),
                    description="Original.",
                    stock=10,
                )
            ]
        )

    def test_applies_only_the_supplied_fields(self):
        draft = ProductDraft.from_mapping({"price": Decimal("13.00")})

        updated = UpdateProduct(products=self.repo).execute(1, draft)

        self.assertEqual(Decimal("13.00"), updated.price)
        self.assertEqual("Original.", updated.description)
        self.assertEqual(10, updated.stock)
        self.assertEqual("Espresso", updated.name)

    def test_reaches_an_inactive_product(self):
        # Otherwise a deactivated product could never be reactivated through the API.
        repo = FakeProductRepository(
            [Product(name="Oculto", price=Decimal("1.00"), is_active=False)]
        )

        updated = UpdateProduct(products=repo).execute(
            1, ProductDraft.from_mapping({"is_active": True})
        )

        self.assertTrue(updated.is_active)

    def test_raises_when_the_product_is_absent(self):
        with self.assertRaises(ProductNotFound):
            UpdateProduct(products=self.repo).execute(999, ProductDraft.from_mapping({"stock": 1}))

    def test_an_update_that_breaks_an_invariant_is_refused(self):
        draft = ProductDraft.from_mapping({"price": Decimal("0")})

        with self.assertRaises(ProductInvalid):
            UpdateProduct(products=self.repo).execute(1, draft)

    def test_a_refused_update_leaves_the_stored_product_untouched(self):
        with self.assertRaises(ProductInvalid):
            UpdateProduct(products=self.repo).execute(
                1, ProductDraft.from_mapping({"price": Decimal("-1")})
            )

        self.assertEqual(Decimal("12.50"), self.repo.get(1).price)


class DeleteProductTests(unittest.TestCase):
    def test_removes_the_product(self):
        repo = FakeProductRepository([Product(name="Efimero", price=Decimal("1.00"))])

        DeleteProduct(products=repo).execute(1)

        self.assertEqual(0, repo.count())

    def test_raises_when_the_product_is_absent(self):
        with self.assertRaises(ProductNotFound):
            DeleteProduct(products=FakeProductRepository()).execute(999)

    def test_reaches_an_inactive_product(self):
        repo = FakeProductRepository(
            [Product(name="Oculto", price=Decimal("1.00"), is_active=False)]
        )

        DeleteProduct(products=repo).execute(1)

        self.assertEqual(0, repo.count())
