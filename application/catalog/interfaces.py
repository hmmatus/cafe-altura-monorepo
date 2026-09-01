from abc import ABC, abstractmethod
from collections.abc import Sequence

from domain.catalog.entities import Product


class ProductRepository(ABC):
    """Persistence port for the catalog.

    Lookups return None when nothing matches rather than raising: turning absence into a domain
    error is the use case's decision, not the adapter's.
    """

    @abstractmethod
    def list_active(self) -> Sequence[Product]:
        """Active products, most recently created first."""

    @abstractmethod
    def get_active(self, product_id: int) -> Product | None:
        """An active product. Read paths use this, so inactive products read as absent."""

    @abstractmethod
    def get(self, product_id: int) -> Product | None:
        """Any product, active or not. Write paths use this, so deactivated rows stay reachable."""

    @abstractmethod
    def add(self, product: Product) -> Product:
        """Persist a new product, returning it with id and created_at filled in."""

    @abstractmethod
    def update(self, product: Product) -> Product:
        """Persist changes to an existing product."""

    @abstractmethod
    def delete(self, product_id: int) -> None:
        """Remove a product permanently."""
