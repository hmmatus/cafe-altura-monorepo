from dataclasses import dataclass, field, fields
from decimal import Decimal
from typing import Any

UNSET: Any = object()
"""Sentinel for "not supplied".

A partial update has to tell "omitted" apart from "explicitly set to empty", and None cannot
carry both meanings.
"""


@dataclass(frozen=True)
class ProductDraft:
    """Input shape for create and update: the writable fields only, no id, no created_at."""

    name: str | Any = UNSET
    price: Decimal | Any = UNSET
    description: str | Any = UNSET
    stock: int | Any = UNSET
    image_url: str | Any = UNSET
    is_active: bool | Any = UNSET

    supplied: frozenset[str] = field(default_factory=frozenset, compare=False)

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> "ProductDraft":
        known = {f.name for f in fields(cls)} - {"supplied"}
        supplied = {key for key in values if key in known}

        return cls(**{key: values[key] for key in supplied}, supplied=frozenset(supplied))

    def changes(self) -> dict[str, Any]:
        """The supplied fields only, ready to merge onto a stored entity."""
        return {name: getattr(self, name) for name in self.supplied}
