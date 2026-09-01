"""Domain tests: pure Python. No Django, no database, no HTTP."""

import dataclasses
import unittest
from decimal import Decimal

from domain.catalog.entities import Product
from domain.catalog.exceptions import ProductInvalid


def _product(**overrides) -> Product:
    defaults = {"name": "Espresso de la Casa", "price": Decimal("12.50")}
    return Product(**{**defaults, **overrides})


class ProductNameTests(unittest.TestCase):
    def test_a_valid_product_constructs(self):
        product = _product()

        self.assertEqual("Espresso de la Casa", product.name)
        self.assertEqual(Decimal("12.50"), product.price)
        self.assertEqual(0, product.stock)
        self.assertTrue(product.is_active)
        self.assertIsNone(product.id)

    def test_empty_name_is_rejected(self):
        with self.assertRaises(ProductInvalid):
            _product(name="")

    def test_whitespace_only_name_is_rejected(self):
        with self.assertRaises(ProductInvalid):
            _product(name="   ")

    def test_name_of_exactly_200_characters_is_accepted(self):
        self.assertEqual(200, len(_product(name="x" * 200).name))

    def test_name_over_200_characters_is_rejected(self):
        with self.assertRaises(ProductInvalid):
            _product(name="x" * 201)


class ProductPriceTests(unittest.TestCase):
    def test_zero_price_is_rejected(self):
        # Stricter than rejecting negatives: a free product is refused too.
        with self.assertRaises(ProductInvalid) as caught:
            _product(price=Decimal("0"))

        self.assertIn("mayor a cero", str(caught.exception))

    def test_negative_price_is_rejected(self):
        with self.assertRaises(ProductInvalid):
            _product(price=Decimal("-5.00"))

    def test_price_with_three_decimals_is_rejected_not_rounded(self):
        with self.assertRaises(ProductInvalid):
            _product(price=Decimal("12.345"))

    def test_smallest_representable_price_is_accepted(self):
        self.assertEqual(Decimal("0.01"), _product(price=Decimal("0.01")).price)

    def test_price_at_the_ceiling_is_accepted(self):
        self.assertEqual(Decimal("99999999.99"), _product(price=Decimal("99999999.99")).price)

    def test_price_above_the_ceiling_is_rejected(self):
        with self.assertRaises(ProductInvalid):
            _product(price=Decimal("100000000.00"))

    def test_a_float_price_is_rejected(self):
        # Accepting a float here would reintroduce the binary drift Decimal exists to avoid.
        with self.assertRaises(ProductInvalid):
            _product(price=12.50)


class ProductStockTests(unittest.TestCase):
    def test_negative_stock_is_rejected(self):
        with self.assertRaises(ProductInvalid):
            _product(stock=-1)

    def test_zero_stock_is_accepted(self):
        self.assertEqual(0, _product(stock=0).stock)


class ProductImmutabilityTests(unittest.TestCase):
    def test_a_product_cannot_be_mutated_in_place(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            _product().name = "otro"

    def test_replacing_a_field_revalidates_every_invariant(self):
        with self.assertRaises(ProductInvalid):
            dataclasses.replace(_product(), price=Decimal("0"))
