from django.urls import path

from interface.api.catalog.views import ProductDetailView, ProductListCreateView

# Explicit routes rather than a DefaultRouter: a router derives its URLs from a ViewSet, and a
# ViewSet derives its behaviour from a queryset — an ORM call inside interface/.
urlpatterns = [
    path("products/", ProductListCreateView.as_view(), name="product-list"),
    path("products/<int:product_id>/", ProductDetailView.as_view(), name="product-detail"),
]
