# Phase 0 Research: Product Catalog

**Feature**: 001-product-catalog | **Date**: 2026-08-11

The Technical Context in [plan.md](./plan.md) carries no NEEDS CLARIFICATION markers — the stack is
fixed by the repository and the data model is settled by the spec. What needed resolving instead
was how to honour a standard-Django source design inside a clean-architecture repository, plus four
correctness details around money, stock, visibility, and error codes.

Two findings below were verified against the installed library source rather than recalled.

---

## D1: Registering `infrastructure/db` as a Django app

**Decision**: Add `infrastructure/db/apps.py` with an `AppConfig` whose `name` is
`infrastructure.db` and whose `label` is `db`, then add `"infrastructure.db"` to `INSTALLED_APPS`.
Models live in `infrastructure/db/models/catalog.py`, imported through
`infrastructure/db/models/__init__.py`.

**Rationale**: `makemigrations` only discovers models inside installed apps. `infrastructure/db/`
exists today but holds only `probes.py`, so nothing has required app registration until now. The
explicit `label = "db"` matters: without it Django derives the label from the last path segment,
which is already `db`, but pinning it prevents a rename of the package from silently renaming every
migration's app label and orphaning the migration history.

A models **package** rather than a single `models.py` keeps one module per business context, so
`orders` and `accounts` later drop in beside `catalog` without a growing file. Django finds them as
long as they are imported in the package's `__init__.py`.

**Alternatives considered**:
- *A top-level `catalog/` Django app, as the source tutorial does.* Rejected — it colocates models,
  serializers, views, and URLs in one package, which is precisely the layering the constitution
  forbids. This was the explicit fork the user resolved in favour of clean architecture.
- *Registering `infrastructure` itself as the app.* Rejected — it would make `external/` part of the
  same app label as persistence, and `external/` holds HTTP clients that will never have models.

---

## D2: Representing money

**Decision**: `Decimal` end to end. `domain.catalog.entities.Product.price` is a `Decimal`;
`ProductModel.price` is a `DecimalField(max_digits=10, decimal_places=2)`; the serializer emits it
as a JSON **string** (`"12.50"`), which is DRF's default.

The entity enforces three things in `__post_init__`: the value is greater than zero, its exponent
is not finer than two decimal places, and it does not exceed 99,999,999.99.

**Rationale**: SC-004 requires zero precision loss across a store-and-retrieve round trip. The
source calls this out at length and it is the one decision in the tutorial worth preserving
verbatim: binary floating point cannot represent 0.1 or 0.2 exactly, so float money accumulates
drift that surfaces as cents appearing and disappearing.

The string representation is the part that is easy to get wrong. **Verified**: DRF's
`COERCE_DECIMAL_TO_STRING` defaults to `True`
(`rest_framework/settings.py:118`, consumed at `rest_framework/fields.py:1107`), so decimals
serialize as strings unless overridden. Keeping that default is deliberate — emitting a JSON number
hands the value to a consumer's float parser and reintroduces the exact drift the `Decimal` was
chosen to avoid. Client code must parse the string with its own decimal type.

`max_digits=10, decimal_places=2` yields eight integer digits: a ceiling of 99,999,999.99, which is
what FR-004 states.

**Alternatives considered**:
- *A `Money` value object wrapping amount and currency.* Rejected for this iteration — the spec
  fixes a single currency, so the currency component would be a constant. Worth revisiting when a
  second currency appears; the entity's validation is the natural seam for it.
- *Storing integer cents.* Rejected — exact, but it forces every read and write site to remember
  the scaling factor, and `DecimalField` already gives exactness without that hazard.
- *Overriding `COERCE_DECIMAL_TO_STRING` to `False` for friendlier JSON.* Rejected as above.

---

## D3: Making negative stock unrepresentable

**Decision**: `ProductModel.stock` is a `PositiveIntegerField(default=0)`. The domain entity
independently rejects a negative stock in `__post_init__`.

**Rationale**: FR-006 requires the constraint at the storage layer, so that no code path — including
a raw query or a future bulk import — can write a negative stock.

**Verified**: on PostgreSQL, Django maps `PositiveIntegerField` to a plain `integer` column *and*
attaches a check constraint. `django/db/backends/postgresql/base.py:117` gives the column type and
line 128 gives `data_type_check_constraints["PositiveIntegerField"] = '"%(column)s" >= 0'`, applied
via `django/db/models/fields/__init__.py:852`. So the generated DDL carries
`CHECK ("stock" >= 0)` — a real database-level guarantee, not merely application-level validation.

The domain check is not redundant: it makes the invariant testable without a database, which
Constitution III requires of use-case tests.

**Alternatives considered**:
- *A plain `IntegerField` with validation only in the serializer.* Rejected — it satisfies neither
  FR-006's "enforced by the storage layer" nor the constitution's placement of invariants in the
  domain.
- *An explicit `CheckConstraint` in `Meta.constraints`.* Rejected as redundant; it would duplicate
  the constraint Django already emits.

---

## D4: Replacing `ModelViewSet` and `DefaultRouter`

**Decision**: Two `APIView` classes and explicit `urlpatterns`.

| View | Route | Methods |
|---|---|---|
| `ProductListCreateView` | `api/products/` | `GET`, `POST` |
| `ProductDetailView` | `api/products/<int:product_id>/` | `GET`, `PUT`, `PATCH`, `DELETE` |

Each method calls exactly one use case from `config.container`.

**Rationale**: `ModelViewSet` derives its behaviour from `queryset = Product.objects.filter(...)` —
an ORM call inside `interface/`, which Constitution I forbids outright and which
`scripts/check_architecture.sh` greps for. There is no configuration of `ModelViewSet` that removes
the coupling; the class exists to bind a view to a model. The same applies to `DefaultRouter`, which
generates routes from a viewset.

The cost is real and worth naming: the five endpoints that `ModelViewSet` provides in two lines
become five use cases, six port methods, and two view classes. That is the price of the boundary,
and it buys use-case tests that run with no database — which is what `tests/application/` already
does for `health`.

This mirrors the existing `HealthView`: `APIView`, one `container` call, no ORM.

**Alternatives considered**:
- *`ModelViewSet` with a repository-backed `get_queryset()`.* Rejected — it still returns a
  `QuerySet` of ORM models into the interface layer, so the entity/model separation collapses at
  the boundary.
- *`GenericAPIView` mixins.* Rejected for the same reason; the mixins assume a queryset.

---

## D5: Whether writes can address an inactive product

**Decision**: Reads are visitor-facing and see active products only. Writes address a product by id
regardless of its active flag. The port exposes both `get_active(product_id)` and
`get(product_id)`.

**Rationale**: FR-015 excludes inactive products from listing *and* single retrieval, so a `GET` on
a deactivated product must return 404 — indistinguishable from one that never existed, per the
spec's edge cases. But `PUT`/`PATCH`/`DELETE` must still reach it, otherwise deactivating a product
through the API would make it permanently unreachable through the API, and reactivating it would be
impossible outside the admin.

Two port methods make the distinction explicit at the boundary rather than hiding it in a flag
argument. Both are called, so Constitution II's ban on speculative port methods holds.

**Alternatives considered**:
- *A single `get(product_id, *, active_only: bool)`.* Rejected — a boolean parameter that changes
  what the method means is harder to read at call sites than two named methods.
- *Letting writes 404 on inactive products too.* Rejected — it strands deactivated products.

---

## D6: Error-code mapping

**Decision**:

| Condition | Raised by | HTTP |
|---|---|---|
| Missing name, wrong type, name over 200 chars, malformed image address | serializer | 400 |
| `price <= 0`, price out of range or over-precise, negative stock | `ProductInvalid` (domain) | 422 |
| Product absent, or inactive on a read path | `ProductNotFound` (domain) | 404 |
| Successful create | — | 201 |
| Successful delete | — | 204 |

**Rationale**: Constitution IV fixes this table: a broken invariant is 422, a serializer shape
failure is DRF's default 400, and a missing entity is 404. Domain exceptions carry no status code;
the view owns the mapping.

This diverges from the source, which puts `price > 0` in `ProductSerializer.validate_price` and so
returns 400 for a zero price. The divergence is deliberate and recorded in plan.md. FR-005's
requirement — refused, with a message stating the price must be greater than zero — is met either
way; only the status code differs.

The practical consequence to keep straight: `{"name": ""}` is a 400 while `{"price": "0"}` is a 422,
even though both feel like "bad input" to a client. The contract documents both.

**Alternatives considered**:
- *422 for everything invalid.* Rejected — it would require suppressing DRF's serializer error
  handling, losing its field-level error bodies.
- *400 for everything, matching the source.* Rejected — it requires the business rule to live in the
  serializer, which Constitution IV forbids.

---

## D7: Pagination

**Decision**: None in this iteration. `GET /api/products/` returns a JSON array of every active
product, ordered newest first.

**Rationale**: The revised spec dropped the paging language that the first draft carried; FR-014
and FR-016 ask for a list in a defined order and nothing more. At the stated scale — hundreds of
products, SC-005's 500-product ceiling — an unpaginated response is well inside the 2-second budget.

Recorded here because it is a known future change: adding pagination later alters the response from
an array to an object, which is a breaking change for consumers. If a client is written against
this contract before then, that break lands on them.

**Alternatives considered**:
- *DRF `PageNumberPagination` now.* Rejected as scope the spec does not ask for, but it is the
  obvious first thing to add when the catalog outgrows the assumption.

---

## D8: Where the admin registration lives

**Decision**: `infrastructure/db/admin.py`, registering `ProductModel` with `list_display`,
`list_editable`, and `search_fields` as the source specifies.

**Rationale**: The Django admin is infrastructure looking at infrastructure — it binds directly to
the ORM model and never touches a use case. Placing it beside the models keeps that coupling
contained in the layer that is allowed to have it. It satisfies FR-021 through FR-024 with no
application-layer involvement.

Note the consequence: admin edits bypass the domain entity, so `price > 0` is **not** enforced for
a staff member editing through the admin — only the database-level `stock >= 0` check applies there.
Closing that gap means either a `ModelForm` with validation or a `CheckConstraint` on price. Left
open deliberately; flagged in data-model.md as a known gap so it is not discovered by accident.

**Alternatives considered**:
- *An admin that calls use cases.* Rejected as significant machinery for an internal tool, and the
  admin's list-editing feature (FR-022) works against querysets, not services.
- *No admin at all, API only.* Rejected — FR-021 through FR-024 require it, and it is the only
  authenticated maintenance path this feature has.

---

## D9: Identity and timestamps in the domain entity

**Decision**: `Product.id` is `int | None` and `Product.created_at` is `datetime | None`; both are
`None` for an entity that has not been persisted. The repository returns a new `Product` carrying
the values the database assigned.

**Rationale**: `CreateProduct` builds a valid `Product` before any row exists, so identity cannot be
required at construction. The database owns id generation (`BigAutoField`) and creation time
(`auto_now_add`), which keeps the timestamp truthful even for rows written outside the use case.

`created_at` is stored but not exposed — FR-018 bounds the response to seven fields, and the source's
serializer field list omits it. It exists to satisfy FR-016's ordering.

**Alternatives considered**:
- *UUID identifiers minted in the domain.* Rejected — the source uses the default integer primary
  key, and nothing in the spec calls for non-sequential ids.
- *A separate `NewProduct` type without id.* Rejected as a second near-identical entity for little
  gain at this size.

---

## Summary of what changes outside this feature's own directories

Four existing files are touched, all additively:

| File | Change |
|---|---|
| `config/settings.py` | add `"infrastructure.db"` to `INSTALLED_APPS` |
| `config/urls.py` | include `interface.api.catalog.urls` under `api/` |
| `config/container.py` | five provider functions |
| `README.md` | note the new endpoints (optional, but the catalog is the first real API surface) |

No existing behaviour changes. The `health` slice is untouched.
