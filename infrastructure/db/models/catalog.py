from django.db import models


class ProductModel(models.Model):
    """Storage shape for a catalog product.

    This is not the domain entity — domain.catalog.entities.Product is. The repository maps
    between them.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    # Money is never a float: binary drift turns cents into rounding errors.
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Emits CHECK ("stock" >= 0) on Postgres, so no code path can store a negative.
    stock = models.PositiveIntegerField(default=0)
    # An address in the external image store. No image bytes are ever held here.
    # 500 rather than the 200 default: object-storage URLs carry long key paths.
    image_url = models.URLField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "catalog_product"
        ordering = ["-created_at"]
        indexes = [
            # Serves the catalog listing: WHERE is_active ORDER BY created_at DESC.
            models.Index(fields=["is_active", "-created_at"], name="catalog_active_recent_idx"),
        ]

    def __str__(self) -> str:
        return self.name
