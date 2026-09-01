# Implementation Plan: Product Catalog

**Branch**: `001-product-catalog` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-product-catalog/spec.md`

## Summary

Add a product catalog: visitors list and retrieve active products (newest first); submissions are
validated before storage; staff maintain products through the Django admin. Product images are
references to an externally hosted file — the system stores an address and never image bytes.

The source material for this feature is a standard-Django tutorial (`startapp catalog`,
`ModelViewSet`, `Product.objects` inside `views.py`). That shape is **not** what gets built. The
data model, validation rules, and scope are taken from the source; the structure follows this
repository's ratified constitution — dependencies point inward, the ORM stays behind a repository,
and business rules live in `domain/`. The user chose this explicitly over following the tutorial
literally.

Concretely, that means `ModelViewSet` and `DefaultRouter` are not used. The five CRUD operations
become five use cases behind explicit `APIView`s, wired in `config/container.py`, exactly as the
existing `health` slice is.

## Technical Context

**Language/Version**: Python 3.12 (in-repo `.venv/`, not auto-activated)

**Primary Dependencies**: Django 6.0.7, Django REST Framework 3.17.1, psycopg 3.3.4,
django-environ 0.14.0. No new runtime dependencies are introduced by this feature.

**Storage**: PostgreSQL 16, reached via `DATABASE_URL` / `env.db()`. Dev instance runs in Docker on
host port 5433.

**Testing**: `python manage.py test` — stdlib `unittest.TestCase` for use-case tests (no database,
no HTTP), `django.test.TestCase` for repository and view tests. Matches the existing `health` tests.

**Target Platform**: Linux/macOS server process behind a WSGI host; local development on macOS.

**Project Type**: Web service (JSON API) with a Django admin for internal maintenance.

**Performance Goals**: Catalog listing and single-product retrieval within 2 seconds for up to 500
products (SC-005).

**Constraints**:
- Monetary values must survive a store-and-retrieve round trip with zero precision loss (SC-004).
  Exact decimals throughout — never binary floating point, at any layer.
- Stock must be impossible to store as negative, enforced at the schema, not only at the edge
  (FR-006).
- Zero image bytes stored, accepted, or served (FR-011, SC-008).
- Write operations ship without access control in this iteration; the feature is **not
  deployable** until FR-025 is satisfied. See Release Gate below.

**Scale/Scope**: Hundreds of products. One entity, five use cases, one admin registration, one new
Django app label for persistence.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates derived from `.specify/memory/constitution.md` v1.0.0.

| Gate | Requirement | Design compliance |
|---|---|---|
| **I. Clean Architecture Boundaries** | `domain/` and `application/` import no framework; `interface/` never touches the ORM; concrete classes named only in `config/container.py` | PASS — `domain/catalog/` is dataclasses and exceptions only; `application/catalog/` holds an ABC port and five use cases; every `.objects` call lives in `infrastructure/db/repositories/catalog.py`; `DjangoProductRepository` is named only in `config/container.py`. Verified by `scripts/check_architecture.sh`. |
| **I. Entity ≠ ORM model** | Repositories translate between persistence shape and entity shape | PASS — `ProductModel` (infrastructure) and `Product` (domain) are separate types; `DjangoProductRepository` maps between them. |
| **I. Business-area naming** | Directories named for business areas, not technical groupings | PASS — the context is `catalog` throughout. |
| **II. Build Inward-Out** | domain → port → use case → model/migration → repository → container → view | PASS — task ordering in Phase 2 follows this; the view is built last. |
| **II. Minimal ports** | Ports declare only methods the current use cases call | PASS — `ProductRepository` declares six methods, each called by one of the five use cases. No speculative surface. |
| **II. Use-case shape** | One class, one public `execute()`, dependencies via `__init__`, no `request`/`Response`/serializer in or out | PASS — five use cases, each taking primitives or a DTO and returning entities. |
| **III. Test-First** | Tests written before implementation and failing first; use-case tests need no DB and no HTTP | PASS — use-case tests run against an in-memory `FakeProductRepository` implementing the port, mirroring `tests/application/health/`. |
| **IV. Explicit Contracts at the Edge** | Domain errors are domain classes carrying no HTTP status; the view owns the mapping | PASS — `ProductInvalid` and `ProductNotFound` in `domain/catalog/exceptions.py`; views map them per the constitution's table. See the deliberate divergence noted below. |
| **IV. Serializers validate shape only** | No business rule inside `validate_*` | PASS — the serializer checks types, required fields, max length, and URL well-formedness. The `price > 0` rule lives on the entity, **not** in a `validate_price` method as the source tutorial had it. |
| **V. Configuration Through Environment** | No hardcoded config, no secrets in source | PASS — this feature introduces no new configuration. |

**Result: PASS.** No violations, so Complexity Tracking is empty.

### Deliberate divergence from the source, recorded

The source tutorial puts the `price > 0` rule in `ProductSerializer.validate_price`, which yields
HTTP 400. Constitution IV classifies a broken invariant as 422 and forbids business rules in
serializers. This plan follows the constitution: `price <= 0` raises `ProductInvalid` from the
entity and the view maps it to **422**, while a missing name or a malformed URL is a shape failure
caught by the serializer and returns **400**. Both are still "refused with a message naming the
field", satisfying FR-005 and FR-020.

### Release Gate — not a constitution gate

FR-025 requires that writes be restricted to administrators before this feature reaches any shared
environment. As planned, `POST`, `PUT`, `PATCH`, and `DELETE` on `/api/products/` are reachable by
anyone. This is intentional for local development and is recorded in the spec's Security Note. It
does not violate the constitution, which is silent on authentication, but it **blocks deployment**.
The implementation must leave FR-025 visible — a module-level comment on the views and an entry in
the feature's completion notes — rather than silently shipping open writes.

## Project Structure

### Documentation (this feature)

```text
specs/001-product-catalog/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── products-api.yaml  # Phase 1 output — OpenAPI contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
domain/catalog/
├── __init__.py
├── entities.py                       # Product — frozen dataclass, invariants in __post_init__
└── exceptions.py                     # ProductInvalid, ProductNotFound

application/catalog/
├── __init__.py
├── dtos.py                           # ProductDraft — input shape for create/update
├── interfaces.py                     # ProductRepository (ABC)
└── services.py                       # ListProducts, GetProduct, CreateProduct,
                                      #   UpdateProduct, DeleteProduct

infrastructure/db/
├── __init__.py
├── apps.py                           # NEW — Django AppConfig, label "db"
├── admin.py                          # NEW — ProductModel admin registration
├── models/
│   ├── __init__.py
│   └── catalog.py                    # ProductModel
├── repositories/
│   ├── __init__.py
│   └── catalog.py                    # DjangoProductRepository
└── migrations/
    ├── __init__.py
    └── 0001_initial.py               # generated

interface/api/catalog/
├── __init__.py
├── serializers.py                    # ProductSerializer, ProductWriteSerializer
├── views.py                          # ProductListCreateView, ProductDetailView
└── urls.py

config/
├── container.py                      # + five provider functions
├── settings.py                       # + "infrastructure.db" in INSTALLED_APPS
└── urls.py                           # + include catalog urls under api/

tests/
├── application/catalog/
│   ├── fakes.py                      # FakeProductRepository (in-memory, implements the port)
│   └── test_services.py              # use-case tests — no DB, no HTTP
├── domain/catalog/
│   └── test_entities.py              # invariant tests — pure, no Django
├── infrastructure/db/repositories/
│   └── test_catalog.py               # entity ↔ row round-trip, real DB
└── interface/api/catalog/
    └── test_views.py                 # status codes and payload shape only
```

**Structure Decision**: The existing four-layer clean architecture layout is reused unchanged; this
feature adds a `catalog` context to each layer, exactly parallel to the existing `health` context.
No top-level Django app is created — `catalog/` at the repository root would put models, views, and
URLs in one package and violate Constitution I.

One structural addition is genuinely new: `infrastructure/db/` currently holds `probes.py` but is
not a registered Django app, because nothing has needed a model until now. It gains an `apps.py`
with label `db` and is added to `INSTALLED_APPS`, which is what lets `makemigrations` discover
`ProductModel`. `tests/domain/` and `tests/infrastructure/` are also new directories.

## Constitution Re-check (post-Phase 1)

Re-evaluated after `research.md`, `data-model.md`, `contracts/products-api.yaml`, and
`quickstart.md` were written. **Still PASS** — the design added no violations. Three points the
design surfaced that the pre-Phase 0 check could not have seen:

1. **Gate I holds structurally.** Every ORM touch is confined to `DjangoProductRepository` and the
   admin, both in `infrastructure/`. `interface/api/catalog/views.py` calls `container` only. The
   `ModelViewSet` that the source used is gone precisely because it cannot satisfy this gate
   (research D4).

2. **Gate IV holds, at a documented cost.** Splitting shape failures (400) from broken invariants
   (422) is what the constitution mandates, and it means `{"price": "0"}` and `{"name": ""}` return
   different status codes for what a client experiences as the same class of mistake. Both are
   documented in the contract with worked examples so the split is discoverable rather than
   surprising.

3. **A gap the boundary creates, recorded rather than hidden.** The Django admin binds to
   `ProductModel` directly, so the domain's `price > 0` invariant does not apply to admin edits —
   and because the repository validates every row while mapping it to an entity, a zero-price row
   written through the admin fails the *entire* catalog listing, not just that product. This is a
   consequence of putting invariants in the domain, which the constitution requires. It is not a
   violation, and closing it (a `CheckConstraint` on price, or an admin `ModelForm`) is left out of
   this feature's scope. It is called out in research D8, data-model.md, and Scenario 7 of
   quickstart.md so it is found on purpose rather than by accident.

## Complexity Tracking

> No Constitution Check violations, before or after design. This section is intentionally empty.
