"""Staff maintenance interface.

⚠️ KNOWN GAP — the admin binds to the ORM model directly, so it bypasses the domain entity and
its invariants. In particular `price > 0` is NOT enforced here; only the database-level
CHECK ("stock" >= 0) applies.

The consequence is sharper than it looks: the repository validates every row while mapping it
to an entity, so a single zero-price row saved through this admin makes the WHOLE catalog
listing fail, not just that product. Closing this needs either a CheckConstraint on price or a
ModelForm with validation. Left open deliberately and recorded here so it is found on purpose.
"""

from django.contrib import admin

from infrastructure.db.models import ProductModel


@admin.register(ProductModel)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock", "is_active")
    list_editable = ("price", "stock", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)
    readonly_fields = ("created_at",)
