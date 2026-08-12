"""View tests: status codes and payload shape only."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from domain.catalog.entities import Product
from infrastructure.db.repositories.catalog import DjangoProductRepository

PRODUCT_FIELDS = {"id", "name", "description", "price", "stock", "image_url", "is_active"}


def _seed(**overrides) -> Product:
    defaults = {"name": "Espresso de la Casa", "price": Decimal("12.50")}
    return DjangoProductRepository().add(Product(**{**defaults, **overrides}))


class ListProductsViewTests(TestCase):
    def test_empty_catalog_returns_an_empty_list_not_an_error(self):
        response = self.client.get(reverse("product-list"))

        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json())

    def test_returns_exactly_the_seven_published_fields(self):
        _seed()

        body = self.client.get(reverse("product-list")).json()

        self.assertEqual(PRODUCT_FIELDS, set(body[0]))
        self.assertNotIn("created_at", body[0])

    def test_price_is_serialized_as_a_string(self):
        _seed(price=Decimal("12.50"))

        price = self.client.get(reverse("product-list")).json()[0]["price"]

        self.assertIsInstance(price, str)
        self.assertEqual("12.50", price)

    def test_inactive_products_are_absent(self):
        _seed(name="Visible")
        _seed(name="Oculto", is_active=False)

        names = [p["name"] for p in self.client.get(reverse("product-list")).json()]

        self.assertEqual(["Visible"], names)

    def test_products_are_ordered_newest_first(self):
        _seed(name="Primero")
        _seed(name="Segundo")

        names = [p["name"] for p in self.client.get(reverse("product-list")).json()]

        self.assertEqual(["Segundo", "Primero"], names)


class GetProductViewTests(TestCase):
    def test_returns_an_active_product(self):
        product = _seed()

        response = self.client.get(reverse("product-detail", args=[product.id]))

        self.assertEqual(200, response.status_code)
        self.assertEqual(PRODUCT_FIELDS, set(response.json()))

    def test_an_inactive_product_and_a_missing_one_are_indistinguishable(self):
        inactive = _seed(is_active=False)

        hidden = self.client.get(reverse("product-detail", args=[inactive.id]))
        missing = self.client.get(reverse("product-detail", args=[999]))

        self.assertEqual(404, hidden.status_code)
        self.assertEqual(404, missing.status_code)
        self.assertEqual(hidden.json(), missing.json())


class CreateProductViewTests(TestCase):
    def _post(self, payload):
        return self.client.post(
            reverse("product-list"), data=payload, content_type="application/json"
        )

    def test_creates_a_valid_product(self):
        response = self._post({"name": "Espresso", "price": "12.50", "stock": 40})

        self.assertEqual(201, response.status_code)
        self.assertEqual(PRODUCT_FIELDS, set(response.json()))
        self.assertEqual("12.50", response.json()["price"])
        self.assertTrue(response.json()["is_active"])

    def test_a_zero_price_is_refused_as_a_broken_rule(self):
        response = self._post({"name": "Gratis", "price": "0"})

        self.assertEqual(422, response.status_code)
        self.assertIn("mayor a cero", response.json()["detail"])

    def test_a_negative_price_is_refused_as_a_broken_rule(self):
        self.assertEqual(422, self._post({"name": "Negativo", "price": "-5.00"}).status_code)

    def test_an_over_precise_price_is_refused_not_rounded(self):
        response = self._post({"name": "Preciso", "price": "12.345"})

        self.assertEqual(422, response.status_code)
        self.assertIn("decimales", response.json()["detail"])

    def test_a_price_above_the_ceiling_is_refused(self):
        self.assertEqual(422, self._post({"name": "Caro", "price": "100000000.00"}).status_code)

    def test_a_negative_stock_is_refused(self):
        response = self._post({"name": "Negativo", "price": "1.00", "stock": -1})

        self.assertEqual(422, response.status_code)

    def test_a_missing_name_is_refused_as_a_malformed_shape(self):
        response = self._post({"price": "12.50"})

        self.assertEqual(400, response.status_code)
        self.assertIn("name", response.json())

    def test_a_name_over_200_characters_is_refused_as_a_malformed_shape(self):
        self.assertEqual(400, self._post({"name": "x" * 201, "price": "1.00"}).status_code)

    def test_a_malformed_image_url_is_refused_as_a_malformed_shape(self):
        response = self._post({"name": "Mala URL", "price": "1.00", "image_url": "not-a-url"})

        self.assertEqual(400, response.status_code)
        self.assertIn("image_url", response.json())

    def test_a_shape_failure_pre_empts_a_broken_rule(self):
        # Both wrong at once: the 400 wins, because shape is validated first.
        response = self._post({"price": "0"})

        self.assertEqual(400, response.status_code)

    def test_nothing_is_stored_after_a_refusal(self):
        self._post({"name": "Gratis", "price": "0"})
        self._post({"price": "12.50"})

        self.assertEqual([], self.client.get(reverse("product-list")).json())


class UpdateProductViewTests(TestCase):
    def setUp(self):
        self.product = _seed(description="Original.", stock=10)

    def _patch(self, payload, product_id=None):
        return self.client.patch(
            reverse("product-detail", args=[product_id or self.product.id]),
            data=payload,
            content_type="application/json",
        )

    def test_patch_changes_only_the_supplied_fields(self):
        response = self._patch({"price": "13.00"})

        self.assertEqual(200, response.status_code)
        self.assertEqual("13.00", response.json()["price"])
        self.assertEqual("Original.", response.json()["description"])
        self.assertEqual(10, response.json()["stock"])

    def test_patch_can_deactivate_a_product(self):
        self._patch({"is_active": False})

        self.assertEqual([], self.client.get(reverse("product-list")).json())

    def test_patch_reaches_an_inactive_product_to_reactivate_it(self):
        # If this 404s, the write path is wrongly using the active-only lookup.
        inactive = _seed(name="Oculto", is_active=False)

        response = self._patch({"is_active": True}, product_id=inactive.id)

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["is_active"])

    def test_patch_refuses_a_price_that_breaks_the_rule(self):
        self.assertEqual(422, self._patch({"price": "0"}).status_code)

    def test_patch_on_an_unknown_product_is_not_found(self):
        self.assertEqual(404, self._patch({"stock": 1}, product_id=999).status_code)

    def test_an_empty_patch_body_is_refused(self):
        self.assertEqual(400, self._patch({}).status_code)

    def test_put_replaces_the_product(self):
        response = self.client.put(
            reverse("product-detail", args=[self.product.id]),
            data={"name": "Reemplazado", "price": "20.00"},
            content_type="application/json",
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("Reemplazado", response.json()["name"])

    def test_put_requires_the_mandatory_fields(self):
        response = self.client.put(
            reverse("product-detail", args=[self.product.id]),
            data={"stock": 5},
            content_type="application/json",
        )

        self.assertEqual(400, response.status_code)


class DeleteProductViewTests(TestCase):
    def test_deletes_a_product(self):
        product = _seed()

        response = self.client.delete(reverse("product-detail", args=[product.id]))

        self.assertEqual(204, response.status_code)
        self.assertEqual([], self.client.get(reverse("product-list")).json())

    def test_deleting_an_unknown_product_is_not_found(self):
        self.assertEqual(404, self.client.delete(reverse("product-detail", args=[999])).status_code)

    def test_deletes_an_inactive_product(self):
        inactive = _seed(is_active=False)

        self.assertEqual(
            204, self.client.delete(reverse("product-detail", args=[inactive.id])).status_code
        )
