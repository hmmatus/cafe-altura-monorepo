"""Repository tests: real database, asserting entity <-> row round-trips."""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from domain.catalog.entities import Product
from infrastructure.db.models import ProductModel
from infrastructure.db.repositories.catalog import DjangoProductRepository


class DjangoProductRepositoryTests(TestCase):
    def setUp(self):
        self.repo = DjangoProductRepository()

    def test_add_fills_id_and_created_at(self):
        stored = self.repo.add(Product(name="Espresso", price=Decimal("12.50")))

        self.assertIsNotNone(stored.id)
        self.assertIsNotNone(stored.created_at)
        self.assertEqual("Espresso", stored.name)

    def test_every_field_survives_the_round_trip(self):
        stored = self.repo.add(
            Product(
                name="Geisha",
                price=Decimal("24.00"),
                description="Lote de altura.",
                stock=12,
                image_url="https://images.example.com/geisha.jpg",
                is_active=True,
            )
        )

        read_back = self.repo.get(stored.id)

        self.assertEqual(stored, read_back)
        self.assertEqual("Lote de altura.", read_back.description)
        self.assertEqual(12, read_back.stock)
        self.assertEqual("https://images.example.com/geisha.jpg", read_back.image_url)

    def test_money_survives_storage_without_precision_loss(self):
        # 0.30 is the classic value binary floating point cannot represent exactly.
        stored = self.repo.add(Product(name="Precision", price=Decimal("0.30")))

        read_back = self.repo.get(stored.id)

        self.assertEqual(Decimal("0.30"), read_back.price)
        self.assertIsInstance(read_back.price, Decimal)

    def test_list_active_excludes_inactive_rows(self):
        self.repo.add(Product(name="Visible", price=Decimal("1.00")))
        self.repo.add(Product(name="Oculto", price=Decimal("1.00"), is_active=False))

        self.assertEqual(["Visible"], [p.name for p in self.repo.list_active()])

    def test_list_active_orders_newest_first(self):
        self.repo.add(Product(name="Primero", price=Decimal("1.00")))
        self.repo.add(Product(name="Segundo", price=Decimal("1.00")))

        self.assertEqual(["Segundo", "Primero"], [p.name for p in self.repo.list_active()])

    def test_list_active_is_empty_when_nothing_is_stored(self):
        self.assertEqual([], list(self.repo.list_active()))

    def test_get_active_hides_an_inactive_product(self):
        stored = self.repo.add(Product(name="Oculto", price=Decimal("1.00"), is_active=False))

        self.assertIsNone(self.repo.get_active(stored.id))

    def test_get_reaches_an_inactive_product(self):
        stored = self.repo.add(Product(name="Oculto", price=Decimal("1.00"), is_active=False))

        self.assertEqual("Oculto", self.repo.get(stored.id).name)

    def test_lookups_return_none_for_an_unknown_id(self):
        self.assertIsNone(self.repo.get(999))
        self.assertIsNone(self.repo.get_active(999))

    def test_update_persists_changes(self):
        stored = self.repo.add(Product(name="Espresso", price=Decimal("12.50")))

        import dataclasses

        self.repo.update(dataclasses.replace(stored, price=Decimal("13.00"), stock=5))

        read_back = self.repo.get(stored.id)
        self.assertEqual(Decimal("13.00"), read_back.price)
        self.assertEqual(5, read_back.stock)

    def test_delete_removes_the_row(self):
        stored = self.repo.add(Product(name="Efimero", price=Decimal("1.00")))

        self.repo.delete(stored.id)

        self.assertIsNone(self.repo.get(stored.id))

    def test_deleting_an_unknown_id_is_harmless(self):
        self.repo.delete(999)  # must not raise


class StockConstraintTests(TestCase):
    def test_the_database_itself_refuses_a_negative_stock(self):
        # FR-006: the guarantee is at the storage layer, not only in the entity.
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductModel.objects.create(name="Negativo", price=Decimal("1.00"), stock=-1)
