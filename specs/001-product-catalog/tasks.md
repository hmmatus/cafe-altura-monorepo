---

description: "Task list for the Product Catalog feature"
---

# Tasks: Product Catalog

**Input**: Design documents from `/specs/001-product-catalog/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/products-api.yaml](./contracts/products-api.yaml), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are **mandatory** for this feature, not optional. Constitution III requires
tests be written before the implementation they cover and fail before they pass. Use-case tests must
run with no database and no HTTP.

**Organization**: Grouped by user story. The shared spine — entity, port, ORM model, repository —
sits in Phase 2 because no story can list, validate, or maintain a product without it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Clean architecture layout at the repository root: `domain/`, `application/`, `infrastructure/`,
`interface/`, `config/`, `tests/`. Paths mirror the layer they belong to. See plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Make `infrastructure/db` a Django app so migrations can discover models, and create the
test packages this feature needs.

- [x] T001 Create `infrastructure/db/apps.py` with an `AppConfig` whose `name` is `"infrastructure.db"` and whose `label` is pinned to `"db"` (research D1 — pinning prevents a package rename from orphaning migration history)
- [x] T002 Add `"infrastructure.db"` to `INSTALLED_APPS` in `config/settings.py`, after `"rest_framework"`
- [x] T003 [P] Create `infrastructure/db/models/__init__.py`, `infrastructure/db/repositories/__init__.py`, and `infrastructure/db/migrations/__init__.py`
- [x] T004 [P] Create `domain/catalog/__init__.py` and `application/catalog/__init__.py`
- [x] T005 [P] Create `interface/api/catalog/__init__.py`
- [x] T006 [P] Create test packages with `__init__.py` in `tests/domain/`, `tests/domain/catalog/`, `tests/application/catalog/`, `tests/infrastructure/`, `tests/infrastructure/db/`, `tests/infrastructure/db/repositories/`, and `tests/interface/api/catalog/`
- [x] T007 Verify `python manage.py check` passes with the new app registered

**Checkpoint**: Django recognizes `infrastructure.db` as an app; no models yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `Product` entity with its invariants, the repository port, the ORM model, and the
adapter. Every user story depends on all four.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

**Build order is fixed by Constitution II**: domain → port → model/migration → repository. Do not
reorder; each step is testable only because the ones above it exist.

### Domain

- [x] T008 [P] Create `domain/catalog/exceptions.py` with `ProductInvalid` and `ProductNotFound`, carrying human-readable messages and **no** HTTP status codes (Constitution IV)
- [x] T009 Write failing invariant tests in `tests/domain/catalog/test_entities.py` covering: empty name rejected; name over 200 characters rejected; `price` of exactly `0` rejected; negative price rejected; price with 3+ decimal places rejected rather than rounded; price above `99999999.99` rejected; negative stock rejected; a valid product constructs. Use stdlib `unittest.TestCase` — no Django import
- [x] T010 Implement `Product` in `domain/catalog/entities.py` as a frozen dataclass with fields `id`, `name`, `description`, `price`, `stock`, `image_url`, `is_active`, `created_at` per data-model.md, enforcing all six invariants in `__post_init__` and raising `ProductInvalid` naming the offending field. Zero framework imports
- [x] T011 Confirm `python manage.py test tests.domain.catalog` passes and that T009's tests failed before T010

### Application

- [x] T012 [P] Create `application/catalog/dtos.py` with `ProductDraft` — the seven writable fields, no `id`, no `created_at`, with unset fields distinguishable from explicitly-`None` fields so `PATCH` can tell "omitted" from "cleared" (data-model.md)
- [x] T013 Create `application/catalog/interfaces.py` with the `ProductRepository` ABC declaring exactly six methods: `list_active()`, `get_active(product_id)`, `get(product_id)`, `add(product)`, `update(product)`, `delete(product_id)`. Lookups return `None` when absent rather than raising — the use case owns that policy. Imports `domain` and `abc` only
- [x] T014 Create `tests/application/catalog/fakes.py` with an in-memory `FakeProductRepository` implementing the port, assigning sequential ids and `created_at` on `add()`, mirroring `tests/application/health/test_check_health.py`'s fake style

### Infrastructure

- [x] T015 Create `ProductModel` in `infrastructure/db/models/catalog.py` per data-model.md: `CharField(max_length=200)`, `TextField(blank=True, default="")`, `DecimalField(max_digits=10, decimal_places=2)`, `PositiveIntegerField(default=0)`, `URLField(blank=True, default="")`, `BooleanField(default=True)`, `DateTimeField(auto_now_add=True)`; `Meta.ordering = ["-created_at"]`; a composite index on `(is_active, created_at)`; `__str__` returning the name (FR-010). Import it in `infrastructure/db/models/__init__.py`
- [x] T016 Generate the migration with `python manage.py makemigrations db` and commit `infrastructure/db/migrations/0001_initial.py` alongside the model
- [x] T017 Verify the storage-level guarantee: `python manage.py sqlmigrate db 0001 | grep -i check` must show `CHECK ("stock" >= 0)`. Its absence means `stock` is not a `PositiveIntegerField` and FR-006 is unmet
- [x] T018 Write failing repository tests in `tests/infrastructure/db/repositories/test_catalog.py` using `django.test.TestCase`: entity ↔ row round-trip preserves every field; `Decimal("0.30")` survives storage and retrieval byte-exact (SC-004); `list_active()` excludes inactive rows and orders newest first; `get_active()` returns `None` for an inactive row while `get()` returns it; `add()` fills `id` and `created_at`
- [x] T019 Implement `DjangoProductRepository` in `infrastructure/db/repositories/catalog.py` implementing the port, with a `_to_entity(row)` mapper. This is the **only** module in the feature permitted to call `.objects`
- [x] T020 Confirm `python manage.py test tests.infrastructure` passes and that T018's tests failed before T019

**Checkpoint**: The entity guarantees its own invariants, and products can be stored and retrieved.
No HTTP surface yet.

---

## Phase 3: User Story 1 - Browse the product catalog (Priority: P1) 🎯 MVP

**Goal**: A caller lists active products newest-first and retrieves any one of them. Inactive
products are invisible.

**Independent Test**: Seed two or three products via the repository, request `GET /api/products/`
and `GET /api/products/{id}/`, confirm every active product appears with all seven fields; deactivate
one and confirm it vanishes and its detail returns 404. No write endpoints needed.

### Tests for User Story 1 ⚠️ Write first, confirm they fail

- [x] T021 [P] [US1] Write use-case tests in `tests/application/catalog/test_services.py` for `ListProducts` (returns what the repository returns, empty list when empty) and `GetProduct` (returns the product; raises `ProductNotFound` when the repository yields `None`), driven by `FakeProductRepository`. No database, no HTTP
- [x] T022 [P] [US1] Write view tests in `tests/interface/api/catalog/test_views.py` for `GET /api/products/`: 200 with an empty array on an empty catalog; active products only; newest first; each item carries exactly the seven fields of the `Product` schema with `created_at` **absent** (FR-018); `price` serialized as a JSON **string**
- [x] T023 [P] [US1] Write view tests for `GET /api/products/{id}/`: 200 for an active product; 404 for an inactive one; 404 for an id that never existed; both 404 bodies identical

### Implementation for User Story 1

- [x] T024 [US1] Implement `ListProducts` and `GetProduct` in `application/catalog/services.py` — one class each, one public `execute()`, repository injected via `__init__`. `GetProduct` raises `ProductNotFound` on a `None` lookup. No `request`, `Response`, or serializer in or out
- [x] T025 [US1] Add `list_products()` and `get_product()` provider functions to `config/container.py`, naming `DjangoProductRepository` — the only place it may be named
- [x] T026 [US1] Create `ProductSerializer` in `interface/api/catalog/serializers.py` as a plain `serializers.Serializer` (not `ModelSerializer` — it serializes the domain entity, not the ORM model) exposing exactly `id`, `name`, `description`, `price`, `stock`, `image_url`, `is_active`. Leave `COERCE_DECIMAL_TO_STRING` at its default so `price` emits as a string (research D2)
- [x] T027 [US1] Create `ProductListCreateView.get` and `ProductDetailView.get` in `interface/api/catalog/views.py` as `APIView` subclasses calling `container` only, mapping `ProductNotFound` → 404. No `.objects`, no business rules, no `ModelViewSet`
- [x] T028 [US1] Create `interface/api/catalog/urls.py` with explicit `urlpatterns` for `products/` and `products/<int:product_id>/` (no `DefaultRouter` — research D4), and include it under `api/` in `config/urls.py`
- [x] T029 [US1] Run `python manage.py test tests.application.catalog tests.interface.api.catalog` and `scripts/check_architecture.sh`; both must pass

**Checkpoint**: A read-only catalog works end to end. This is the MVP and is demonstrable on its own.

---

## Phase 4: User Story 2 - Reject invalid product data (Priority: P2)

**Goal**: Submissions are checked before storage. A price at or below zero is refused with a message
saying so; nothing invalid reaches the database.

**Independent Test**: `POST` a product with price `"0"`, then `"-5.00"`, then `"12.345"`, then a
valid one — the first three are refused, the fourth is stored. Confirm the catalog is unchanged
after the refusals.

**Note on status codes**: shape failures are 400 (DRF serializer), broken invariants are 422
(domain). This diverges deliberately from the source tutorial's `validate_price` returning 400 —
see research D6 and the Constitution IV note in plan.md.

### Tests for User Story 2 ⚠️ Write first, confirm they fail

- [x] T030 [P] [US2] Add use-case tests to `tests/application/catalog/test_services.py` for `CreateProduct`: a valid draft is persisted and returned with an assigned id; a draft with a zero price propagates `ProductInvalid` from the entity and calls the repository **not at all**
- [x] T031 [P] [US2] Add view tests to `tests/interface/api/catalog/test_views.py` for `POST /api/products/`: 201 with the seven-field body; 422 for price `"0"`, `"-5.00"`, `"12.345"`, and `"100000000.00"`; 400 for a missing `name`, a `name` over 200 characters, and a malformed `image_url`; the catalog is empty after every refusal
- [x] T032 [P] [US2] Add a view test asserting a 422 body carries a `detail` message naming the price rule, and a 400 body carries DRF's field-keyed error shape — the two error bodies are structurally different and both are in the contract

### Implementation for User Story 2

- [x] T033 [US2] Implement `CreateProduct` in `application/catalog/services.py` taking a `ProductDraft`, constructing a `Product` (which raises `ProductInvalid` on a broken invariant, uncaught by design) and calling `repository.add()`
- [x] T034 [US2] Add a `create_product()` provider to `config/container.py`
- [x] T035 [US2] Create `ProductWriteSerializer` in `interface/api/catalog/serializers.py` validating **shape only**: `name` required and ≤200 characters, `price` as a `DecimalField`, `stock` as an integer, `image_url` as a URL, `description` and `is_active` optional with defaults. It MUST NOT contain a `validate_price` business rule (Constitution IV) — that rule lives on the entity
- [x] T036 [US2] Implement `ProductListCreateView.post` in `interface/api/catalog/views.py`: validate with `ProductWriteSerializer` (`raise_exception=True` → 400), build a `ProductDraft`, call the use case, catch `ProductInvalid` → 422 with a `detail` body, return 201 with `ProductSerializer`
- [x] T037 [US2] Run `python manage.py test tests.application.catalog tests.interface.api.catalog`; confirm every refusal leaves the catalog untouched

**Checkpoint**: The write path validates. Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Maintain the catalog (Priority: P3)

**Goal**: Staff create, correct, deactivate, and remove products — through the admin, and through
the remaining API verbs.

**Independent Test**: Through the admin, create a product, edit its price and stock from the list
view, search it by name, untick active, and confirm it leaves the visitor-facing catalog while its
record remains. Through the API, `PATCH` a deactivated product back to active.

### Tests for User Story 3 ⚠️ Write first, confirm they fail

- [x] T038 [P] [US3] Add use-case tests to `tests/application/catalog/test_services.py` for `UpdateProduct` (merges a partial draft onto the stored entity and re-runs invariants; raises `ProductNotFound` when absent; raises `ProductInvalid` when the merge breaks a rule) and `DeleteProduct` (raises `ProductNotFound` when absent)
- [x] T039 [P] [US3] Add view tests to `tests/interface/api/catalog/test_views.py` for `PUT`, `PATCH`, and `DELETE`: 200 / 200 / 204 on success; 404 for an unknown id; 422 for a `PATCH` setting price to `"0"`; and — the one that catches the wrong repository method — a `PATCH` reactivating an **inactive** product returns 200, not 404 (research D5)
- [x] T040 [P] [US3] Add a view test asserting `PATCH` with a single field leaves the other stored fields unchanged

### Implementation for User Story 3

- [x] T041 [US3] Implement `UpdateProduct` and `DeleteProduct` in `application/catalog/services.py`, both resolving through `repository.get()` — **not** `get_active()`, so deactivated products stay reachable on the write path
- [x] T042 [US3] Add `update_product()` and `delete_product()` providers to `config/container.py`
- [x] T043 [US3] Extend `interface/api/catalog/serializers.py` so partial updates are supported (all fields optional on `PATCH`, required on `PUT`) per the `ProductPatch` and `ProductWrite` schemas in the contract
- [x] T044 [US3] Implement `ProductDetailView.put`, `.patch`, and `.delete` in `interface/api/catalog/views.py`, mapping `ProductNotFound` → 404, `ProductInvalid` → 422, and returning 204 with no body on delete
- [x] T045 [US3] Create `infrastructure/db/admin.py` registering `ProductModel` with `list_display = ("name", "price", "stock", "is_active")`, `list_editable = ("price", "stock", "is_active")`, and `search_fields = ("name",)` (FR-021 to FR-023)
- [x] T046 [US3] Add a module-level comment to `infrastructure/db/admin.py` recording that admin edits bypass the domain entity, so `price > 0` is not enforced there, and that a zero-price row breaks the whole catalog listing on read (research D8, data-model.md)
- [x] T047 [US3] Run `python manage.py test` in full; all stories must pass together

**Checkpoint**: All three stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T048 Add a module-level comment to `interface/api/catalog/views.py` recording FR-025: the write operations have no authentication or authorization, this is deliberate for local development, and the feature must not be deployed until writes are restricted to administrators
- [x] T049 [P] Update `README.md` with the catalog endpoints and the two things a consumer will get wrong otherwise: prices are JSON strings, and the listing is unpaginated (an array today, an object once pagination lands)
- [x] T050 [P] Update `CLAUDE.md`'s Layout section to name `catalog` as a second context alongside `health`
- [x] T051 Run `ruff format .` and `ruff check --fix .` until clean
- [x] T052 Run `scripts/check_architecture.sh`; expect `Architecture boundaries OK.` Then run its two greps by hand — `grep -rnE '^\s*(from|import)\s+(django|rest_framework)' domain/ application/` and `grep -rn '\.objects' interface/` — both must be empty
- [~] T053 Work through every scenario in [quickstart.md](./quickstart.md), including Scenario 7's admin gap and Scenario 8's from-nothing migration run
- [x] T054 Verify the full pre-push gate passes: `scripts/check_architecture.sh && python manage.py test`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup. **Blocks all three user stories**
- **User Stories (Phases 3–5)**: All depend on Foundational
- **Polish (Phase 6)**: Depends on the stories you intend to ship

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only. No dependency on US2 or US3
- **US2 (P2)**: Depends on Foundational only. Reuses `ProductSerializer` from T026 for its 201 response — if US2 is built before US1, move T026 into this phase
- **US3 (P3)**: Depends on Foundational only. Its `PATCH` tests read back through the list endpoint, which is US1's; testable via the repository directly if US1 is skipped

The three stories touch two shared files — `application/catalog/services.py` and
`interface/api/catalog/views.py` — so parallel work across stories means edits to the same files.
They are additive (separate classes, separate methods), but do not run T024, T033, and T041
simultaneously without coordination.

### Within Each Story

Tests before implementation, and confirm they fail first (Constitution III). Then: use case →
container provider → serializer → view → urls. Never the reverse; writing the view first is a
stop-and-rebuild condition per the `django-endpoint-creator` skill.

### Parallel Opportunities

- **Phase 1**: T003, T004, T005, T006 all touch different directories
- **Phase 2**: T008 and T012 are independent. T009 must precede T010; T018 must precede T019
- **Phase 3**: T021, T022, T023 are three independent test tasks
- **Phase 4**: T030, T031, T032 likewise
- **Phase 5**: T038, T039, T040 likewise
- **Phase 6**: T049 and T050 are different files

---

## Parallel Example: User Story 1

```bash
# Write all three test tasks together, then confirm they fail:
Task: "Use-case tests for ListProducts and GetProduct in tests/application/catalog/test_services.py"
Task: "View tests for GET /api/products/ in tests/interface/api/catalog/test_views.py"
Task: "View tests for GET /api/products/{id}/ in tests/interface/api/catalog/test_views.py"

python manage.py test tests.application.catalog tests.interface.api.catalog   # must FAIL

# Then implement T024 → T028 in order; the ordering is a constitution requirement, not a preference.
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1: Setup — T001 to T007
2. Phase 2: Foundational — T008 to T020 (**critical, blocks everything**)
3. Phase 3: User Story 1 — T021 to T029
4. **STOP and VALIDATE**: quickstart Scenarios 1 and 5. A read-only catalog is a shippable slice
5. Do **not** deploy — FR-025 is open only once write endpoints exist, so a read-only MVP is
   actually the one increment here that is safe to expose

### Incremental Delivery

1. Setup + Foundational → the entity and its storage are proven
2. Add US1 → read-only catalog → demo (MVP)
3. Add US2 → validation demonstrable live → demo, **local only from here on**
4. Add US3 → staff maintenance → demo, local only
5. Polish → FR-025 recorded in code, docs updated, quickstart walked end to end

### Notes

- Phase 2 is unusually large relative to the stories. That is the shape of this architecture, not a
  planning error: the entity, port, model, and repository are shared by all three stories, and
  building them per-story would mean building them three times
- Commit after each task or logical group. The migration (T016) must be committed with the model
  (T015) in the same commit, per CLAUDE.md
- The pre-push hook runs `scripts/check_architecture.sh` and `manage.py test`. Do not bypass with
  `--no-verify`
- **This feature is not deployable when complete.** FR-025 leaves create, update, and delete open to
  any caller. T048 records that in the code so it cannot be lost

---

## Convergence — state at completion (2026-08-12)

53 of 54 tasks complete. Verified: 85 tests pass, `scripts/check_architecture.sh` reports
`Architecture boundaries OK.`, `ruff check` clean, and quickstart Scenarios 1–6 confirmed against a
live server on port 8123 (create, zero-price 422, over-precise 422, missing-name 400, `0.30`
round-trip, deactivate/reactivate, identical 404s, delete 204).

**T053 is partial.** Two quickstart scenarios were not executed:

- **Scenario 7 (admin UI)** — needs an interactive browser login. The admin registration and its
  documented bypass gap exist in `infrastructure/db/admin.py`, but nobody has clicked through the
  list-editable columns or confirmed the zero-price bypass by hand.
- **Scenario 8 (`docker compose down -v`)** — destroys the dev database volume, and `compose.yaml`
  is not on `main` (it lives on the unmerged `chore/postgres-colima-compose` branch). Migrations
  were confirmed to apply cleanly to a fresh **test** database on every test run, which covers
  SC-010 in substance but not the exact from-nothing procedure.

**Known gap carried forward, no task exists for it**: SC-005 (listing within 2s at 500 products) has
no automated coverage. The composite index on `(is_active, -created_at)` is in place, but nothing
measures the criterion. Flagged in the analysis pass as finding G1; adding a seeded-volume benchmark
is the obvious follow-up.

**Deviations from the plan, both driven by what the libraries actually do**:

1. `image_url` is `URLField(max_length=500)` rather than the Django default of 200. Object-storage
   URLs carry long key paths, and 200 characters is a real ceiling for signed or deeply-nested keys.
2. `ProductWriteSerializer.price` uses `max_digits=None, decimal_places=None`. DRF's `DecimalField`
   *quantizes* to `decimal_places`, which silently rounded `"12.345"` to two places and let it
   through as valid — the exact silent-rounding failure this design exists to prevent. Disabling
   quantization lets the raw value reach the entity, which refuses it with a 422. The read
   serializer still quantizes to the two decimals the contract publishes.
