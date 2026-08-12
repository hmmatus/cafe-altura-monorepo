from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from domain.catalog.exceptions import ProductInvalid

NAME_MAX_LENGTH = 200
PRICE_MAX = Decimal("99999999.99")
PRICE_DECIMAL_PLACES = 2


@dataclass(frozen=True)
class Product:
    """An item offered for sale.

    Frozen, and every invariant runs in __post_init__, so there is no path to a Product in an
    invalid state — including through dataclasses.replace().

    `id` and `created_at` are None until the row exists; the database owns both.
    """

    name: str
    price: Decimal
    description: str = ""
    stock: int = 0
    image_url: str = ""
    is_active: bool = True
    id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        self._check_name()
        self._check_price()
        self._check_stock()

    def _check_name(self) -> None:
        if not self.name or not self.name.strip():
            raise ProductInvalid("El nombre es obligatorio.")

        if len(self.name) > NAME_MAX_LENGTH:
            raise ProductInvalid(f"El nombre admite como máximo {NAME_MAX_LENGTH} caracteres.")

    def _check_price(self) -> None:
        # A float here would carry binary rounding drift into stored money.
        if not isinstance(self.price, Decimal):
            raise ProductInvalid("El precio debe ser un decimal exacto.")

        if self.price <= 0:
            raise ProductInvalid("El precio debe ser mayor a cero.")

        if -self.price.as_tuple().exponent > PRICE_DECIMAL_PLACES:
            raise ProductInvalid(f"El precio admite como máximo {PRICE_DECIMAL_PLACES} decimales.")

        if self.price > PRICE_MAX:
            raise ProductInvalid(f"El precio no puede superar {PRICE_MAX}.")

    def _check_stock(self) -> None:
        if not isinstance(self.stock, int) or isinstance(self.stock, bool):
            raise ProductInvalid("El stock debe ser un número entero.")

        if self.stock < 0:
            raise ProductInvalid("El stock no puede ser negativo.")
