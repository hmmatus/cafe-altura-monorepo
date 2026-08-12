# Phase 1 Data Model: Product Catalog

**Feature**: 001-product-catalog | **Date**: 2026-08-11

One entity, no relationships. Decisions behind the field choices are in [research.md](./research.md);
this document is the shape itself.

---

## Domain entity — `domain/catalog/entities.py`

`Product` is a frozen dataclass with zero framework imports. It is the business shape: what a
product *is*, independent of how it is stored or serialized.

| Field | Type | Optional | Notes |
|---|---|---|---|
| `id` | `int \| None` | yes | `None` until persisted; assigned by the database |
| `name` | `str` | no | 1–200 characters after stripping |
| `description` | `str` | yes | defaults to `""` |
| `price` | `Decimal` | no | > 0, at most 2 decimal places, at most 99,999,999.99 |
| `stock` | `int` | no | ≥ 0, defaults to 0 |
| `image_url` | `str` | yes | defaults to `""`; an address in the external image store |
| `is_active` | `bool` | no | defaults to `True` |
| `created_at` | `datetime \| None` | yes | `None` until persisted; set by the database |

### Invariants, enforced in `__post_init__`

Each raises `ProductInvalid` with a message naming the field.

1. **`name` is present** — non-empty after stripping surrounding whitespace. *(FR-002)*
2. **`name` is at most 200 characters.** *(FR-002)*
3. **`price` is greater than zero** — a price of exactly `0` is refused, not only negatives.
   Message: *the price must be greater than zero*. *(FR-005)*
4. **`price` has at most two decimal places** — checked on the `Decimal` exponent, so `12.345` is
   refused rather than silently rounded. *(FR-004)*
5. **`price` is at most 99,999,999.99.** *(FR-004)*
6. **`stock` is not negative.** *(FR-006)*

Frozen, so an update produces a new instance and the invariants re-run on every construction —
there is no path to a `Product` in an invalid state.

### Domain exceptions — `domain/catalog/exceptions.py`

```
ProductInvalid   — an invariant was broken. Carries a human-readable message. → 422
ProductNotFound  — no product with that identifier is reachable on this path. → 404
```

Neither carries an HTTP status code; the view owns that mapping, per Constitution IV.

---

## Input DTO — `application/catalog/dtos.py`

`ProductDraft` is the input shape for create and update: the seven writable fields, with no `id`
and no `created_at`. It exists so use cases take a single typed argument instead of six positional
parameters, and so `interface/` has something to hand inward that is not a serializer.

For `PATCH`, unset fields are represented as absent rather than as `None`, so that "not supplied"
is distinguishable from "explicitly cleared". `UpdateProduct` merges the draft onto the stored
entity before reconstructing it, which re-runs every invariant.

---

## Persistence model — `infrastructure/db/models/catalog.py`

`ProductModel` is the storage shape. It is **not** the entity; `DjangoProductRepository` maps
between them.

| Column | Django field | DDL consequence |
|---|---|---|
| `id` | `BigAutoField` (implicit) | `bigint` primary key |
| `name` | `CharField(max_length=200)` | `varchar(200) NOT NULL` |
| `description` | `TextField(blank=True, default="")` | `text NOT NULL` |
| `price` | `DecimalField(max_digits=10, decimal_places=2)` | `numeric(10, 2) NOT NULL` |
| `stock` | `PositiveIntegerField(default=0)` | `integer NOT NULL` + `CHECK ("stock" >= 0)` |
| `image_url` | `URLField(blank=True, default="")` | `varchar NOT NULL` |
| `is_active` | `BooleanField(default=True)` | `boolean NOT NULL` |
| `created_at` | `DateTimeField(auto_now_add=True)` | `timestamptz NOT NULL` |

`Meta.ordering = ["-created_at"]` gives FR-016's newest-first default. `__str__` returns the name,
so the admin shows *Café Altura Geisha* rather than *Product object (1)* — FR-010.

**Indexes**: `is_active` and `created_at` are both in the hot path of the catalog listing
(`WHERE is_active = true ORDER BY created_at DESC`). A composite index on `(is_active, created_at)`
serves it directly. At the stated scale of hundreds of products this is not yet load-bearing —
Postgres will happily sequential-scan — but it costs nothing now and avoids a later migration on a
table that will only grow.

### Where the model is stricter, and where it is not

The check constraint on `stock` is a genuine database guarantee: no code path can write a negative
stock. **There is no equivalent database constraint on `price`.** The `price > 0` rule lives only in
the domain entity, so it holds for every path that goes through a use case — the API — and does not
hold for the Django admin, which binds to the model directly.

This is a real, known gap, called out in research D8. A staff member can set a price of `0` through
the admin. Closing it means either a `CheckConstraint(price__gt=0)` on the model or an admin
`ModelForm` with validation. Deliberately left open here rather than discovered later.

---

## Repository port — `application/catalog/interfaces.py`

`ProductRepository` is an ABC in the application layer. Six methods, each called by exactly one use
case — no speculative surface, per Constitution II.

| Method | Returns | Used by |
|---|---|---|
| `list_active()` | `Sequence[Product]`, newest first | `ListProducts` |
| `get_active(product_id)` | `Product \| None` | `GetProduct` |
| `get(product_id)` | `Product \| None`, active or not | `UpdateProduct`, `DeleteProduct` |
| `add(product)` | `Product` with id and `created_at` filled | `CreateProduct` |
| `update(product)` | `Product` | `UpdateProduct` |
| `delete(product_id)` | `None` | `DeleteProduct` |

The split between `get_active` and `get` is what makes FR-015 hold for reads without stranding
deactivated products on the write path — research D5.

The port returns `None` for a missing product rather than raising; the use case decides that absence
means `ProductNotFound`. Keeping the port free of domain-error policy leaves fakes trivial to write.

---

## Use cases — `application/catalog/services.py`

Five classes, each with one public `execute()`, dependencies injected via `__init__`.

| Use case | Input | Output | Raises |
|---|---|---|---|
| `ListProducts` | — | `Sequence[Product]` | — |
| `GetProduct` | `product_id: int` | `Product` | `ProductNotFound` |
| `CreateProduct` | `ProductDraft` | `Product` | `ProductInvalid` |
| `UpdateProduct` | `product_id: int`, `ProductDraft` | `Product` | `ProductNotFound`, `ProductInvalid` |
| `DeleteProduct` | `product_id: int` | `None` | `ProductNotFound` |

`ProductInvalid` propagates from the entity's constructor rather than being raised by the use case —
the invariants are the entity's, and the use case simply does not catch them.

---

## Mapping between the layers

`DjangoProductRepository._to_entity(row)` builds a `Product` from a `ProductModel`. Because the
entity validates on construction, a row that somehow violates an invariant — written before the rule
existed, or through the admin — raises `ProductInvalid` on read.

That is a deliberate trade and it has a sharp edge worth stating: a zero-price product created
through the admin will make the catalog listing fail, not just that one product. The listing maps
every row. Mitigation is to close the admin gap above; the alternative — a lenient read path that
constructs entities without validation — would mean the domain type no longer guarantees its own
invariants, which is worse.

Nothing else in the system references `Product`, so no other mapping exists.

---

## State

`is_active` is the only state a product carries.

```
active  ──deactivate──>  inactive
        <──reactivate──
```

- Both transitions are edits to a single flag; there is no workflow, no approval, no draft state.
- A newly created product is **active** (`is_active` defaults to `True`). This follows the source.
  Note it differs from the withdrawn first draft of the spec, which created products unpublished —
  that requirement did not survive into the agreed model.
- Deactivating removes a product from the visitor-facing catalog while retaining its record —
  FR-024. It does not delete.
- Hard deletion exists via `DELETE` and destroys history. The spec permits it and flags
  deactivation as the intended path.
