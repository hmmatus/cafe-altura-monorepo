"""Catalog HTTP adapter.

⚠️ FR-025 — UNPROTECTED WRITE PATH, DELIBERATE AND TEMPORARY.

POST, PUT, PATCH and DELETE below carry no authentication and no authorization. Any caller who
can reach this service can rewrite prices, alter stock, or delete the catalog outright.

This is acceptable ONLY on a local development machine, and only while the validation behaviour
of User Story 2 is being demonstrated. Restricting writes to administrators is a RELEASE
BLOCKER, not a follow-up improvement. Do not deploy this feature to any shared or public
environment until that is done.
"""

from rest_framework import status as http
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from application.catalog.dtos import ProductDraft
from config import container
from domain.catalog.exceptions import ProductInvalid, ProductNotFound
from interface.api.catalog.serializers import ProductSerializer, ProductWriteSerializer


def _invalid(exc: ProductInvalid) -> Response:
    # A broken invariant is 422; a malformed request shape is DRF's own 400.
    return Response({"detail": str(exc)}, status=http.HTTP_422_UNPROCESSABLE_ENTITY)


def _not_found() -> Response:
    return Response({"detail": "No existe ese producto."}, status=http.HTTP_404_NOT_FOUND)


class ProductListCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        products = container.list_products().execute()

        return Response(ProductSerializer(products, many=True).data)

    def post(self, request):
        payload = ProductWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        try:
            product = container.create_product().execute(
                ProductDraft.from_mapping(payload.validated_data)
            )
        except ProductInvalid as exc:
            return _invalid(exc)

        return Response(ProductSerializer(product).data, status=http.HTTP_201_CREATED)


class ProductDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, product_id: int):
        try:
            product = container.get_product().execute(product_id)
        except ProductNotFound:
            return _not_found()

        return Response(ProductSerializer(product).data)

    def put(self, request, product_id: int):
        return self._write(request, product_id, partial_update=False)

    def patch(self, request, product_id: int):
        return self._write(request, product_id, partial_update=True)

    def delete(self, request, product_id: int):
        try:
            container.delete_product().execute(product_id)
        except ProductNotFound:
            return _not_found()

        return Response(status=http.HTTP_204_NO_CONTENT)

    @staticmethod
    def _write(request, product_id: int, *, partial_update: bool) -> Response:
        payload = ProductWriteSerializer(data=request.data, partial_update=partial_update)
        payload.is_valid(raise_exception=True)

        try:
            product = container.update_product().execute(
                product_id, ProductDraft.from_mapping(payload.validated_data)
            )
        except ProductNotFound:
            return _not_found()
        except ProductInvalid as exc:
            return _invalid(exc)

        return Response(ProductSerializer(product).data)
