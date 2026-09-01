"""Catalog domain errors.

These carry business meaning, never transport encoding. The view owns the mapping to HTTP.
"""


class CatalogError(Exception):
    """Base for every catalog domain error."""


class ProductInvalid(CatalogError):
    """A product invariant was broken."""


class ProductNotFound(CatalogError):
    """No product with that identifier is reachable on this path."""
