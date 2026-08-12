# Quickstart: Product Catalog

**Feature**: 001-product-catalog | **Date**: 2026-08-11

How to run and prove this feature works end to end. Field definitions live in
[data-model.md](./data-model.md); the wire format lives in
[contracts/products-api.yaml](./contracts/products-api.yaml). This document is the validation
script, not the implementation.

---

## Prerequisites

```bash
colima start                          # container runtime; Docker Desktop stays off
docker compose up -d                  # dev Postgres on host port 5433
source .venv/bin/activate             # the venv is never auto-activated
```

> On `main` there is no `compose.yaml` yet — it lives on the unmerged
> `chore/postgres-colima-compose` branch. Until that merges, start the database with the
> `docker run` invocation in README.md. Either way, Postgres must answer on **5433**.

Confirm `.env` carries `DATABASE_URL=postgres://cafe:cafe@localhost:5433/cafe_altura`.

Check the database is reachable before going further — the health endpoint already answers this:

```bash
python manage.py runserver
curl -s localhost:8000/api/health/
```

Expect `{"status": "ok", "components": [{"name": "database", "healthy": true, ...}]}`. A 503 here
means the database is down, and every step below will fail for that reason rather than any reason
to do with the catalog.

---

## Setup

```bash
python manage.py makemigrations db    # generates the catalog migration
python manage.py migrate
python manage.py createsuperuser      # for the admin checks
python manage.py runserver
```

`makemigrations` writing nothing means `"infrastructure.db"` is missing from `INSTALLED_APPS` —
Django only discovers models inside installed apps.

Confirm the storage-level guarantee landed. This is FR-006, and it is worth seeing rather than
assuming:

```bash
python manage.py sqlmigrate db 0001 | grep -i check
```

Expect a `CHECK ("stock" >= 0)` clause. If it is absent, `stock` is not a `PositiveIntegerField`.

---

## Automated verification

The real gate. Everything below it is manual confirmation of the same behaviour.

```bash
python manage.py test                 # full suite
python manage.py test tests.domain.catalog          # invariants, no Django
python manage.py test tests.application.catalog     # use cases, no DB, no HTTP
python manage.py test tests.infrastructure          # entity ↔ row round-trips
python manage.py test tests.interface.api.catalog   # status codes and payload shape
```

Then the boundary check, which is what stops this feature from quietly becoming the tutorial's
architecture:

```bash
scripts/check_architecture.sh         # expect: Architecture boundaries OK.
```

Two greps it runs, worth knowing by hand:

```bash
grep -rnE '^\s*(from|import)\s+(django|rest_framework)' domain/ application/   # must be empty
grep -rn '\.objects' interface/                                               # must be empty
```

A non-empty result from either means the ORM or the framework has leaked inward, and the fix is to
move the code, not to loosen the check.

---

## Scenario 1 — Empty catalog (FR-017)

```bash
curl -s localhost:8000/api/products/
```

Expect `[]`. An empty catalog is not an error.

---

## Scenario 2 — Create a product (FR-019, User Story 2)

```bash
curl -s -X POST localhost:8000/api/products/ \
  -H 'Content-Type: application/json' \
  -d '{"name": "Espresso de la Casa", "price": "12.50", "stock": 40}'
```

Expect **201** and a body carrying exactly seven fields: `id`, `name`, `description`, `price`,
`stock`, `image_url`, `is_active`. Confirm:

- `price` comes back as the **string** `"12.50"`, not the number `12.50`. This is deliberate — see
  research D2.
- `is_active` is `true`; new products are active immediately.
- `description` and `image_url` are `""`, never `null`.
- `created_at` is **absent**. It is stored, but FR-018 bounds the response to seven fields.

---

## Scenario 3 — Validation refuses bad data (User Story 2, FR-005, FR-020)

The scenario the source most wanted to see live. Note that the two failure modes carry **different
status codes**, and that difference is the design working as intended, not an inconsistency.

A business rule broken — **422**:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/api/products/ \
  -H 'Content-Type: application/json' -d '{"name": "Gratis", "price": "0"}'      # 422

curl -s -X POST localhost:8000/api/products/ \
  -H 'Content-Type: application/json' -d '{"name": "Negativo", "price": "-5.00"}'
```

Expect 422 with a `detail` message stating the price must be greater than zero. A price of exactly
zero is refused, not only negatives.

A malformed shape — **400**:

```bash
curl -s -X POST localhost:8000/api/products/ \
  -H 'Content-Type: application/json' -d '{"price": "12.50"}'                    # name missing

curl -s -X POST localhost:8000/api/products/ \
  -H 'Content-Type: application/json' \
  -d '{"name": "Mala URL", "price": "12.50", "image_url": "not-a-url"}'
```

Expect 400 with DRF's field-level body, e.g. `{"name": ["This field is required."]}`.

Over-precision and range — **422**:

```bash
curl -s -X POST localhost:8000/api/products/ \
  -H 'Content-Type: application/json' -d '{"name": "Preciso", "price": "12.345"}'
```

Expect 422. The value must be refused, **not** silently rounded to `12.35` — that silent rounding is
the failure mode this whole decimal design exists to prevent.

After all of these, confirm nothing was stored:

```bash
curl -s localhost:8000/api/products/ | python -m json.tool
```

Only the product from Scenario 2 should be present.

---

## Scenario 4 — Money survives the round trip (SC-004)

```bash
curl -s -X POST localhost:8000/api/products/ \
  -H 'Content-Type: application/json' -d '{"name": "Precision", "price": "0.30", "stock": 1}'
```

Retrieve it and confirm the price is exactly `"0.30"`. Values like `0.1`, `0.2`, and `0.3` are the
ones binary floating point cannot represent exactly; if any layer has silently become a float, this
is where it shows — as `0.30000000000000004` or a value that fails to compare equal to itself after
a round trip.

---

## Scenario 5 — Listing order and active filtering (FR-015, FR-016)

Create a second product, then:

```bash
curl -s localhost:8000/api/products/ | python -m json.tool
```

Expect the **most recently created first**. Then deactivate the newer one and re-list:

```bash
curl -s -X PATCH localhost:8000/api/products/2/ \
  -H 'Content-Type: application/json' -d '{"is_active": false}'

curl -s localhost:8000/api/products/          # the deactivated product is gone
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/products/2/   # 404
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/products/999/ # 404 — same response
```

Both 404s must be indistinguishable: an inactive product and one that never existed look identical
to a caller.

Then confirm the write path still reaches it — this is the point of the `get` / `get_active` split
in research D5:

```bash
curl -s -X PATCH localhost:8000/api/products/2/ \
  -H 'Content-Type: application/json' -d '{"is_active": true}'    # 200, reactivated
```

If this returns 404, writes are wrongly using the active-only lookup and deactivated products are
stranded.

---

## Scenario 6 — Missing images degrade, they do not fail (FR-013)

```bash
curl -s -X POST localhost:8000/api/products/ \
  -H 'Content-Type: application/json' \
  -d '{"name": "Imagen rota", "price": "9.00", "image_url": "https://images.example.com/gone.jpg"}'
```

The address does not resolve. Expect **201** anyway, and expect the product to list normally. The
service stores an address; it never fetches it, never validates that it resolves, and never holds
image bytes.

---

## Scenario 7 — Admin maintenance (User Story 3, FR-021 to FR-024)

Open `http://localhost:8000/admin/` and sign in.

- The product list shows **name, price, stock, active** as columns (FR-021).
- Price, stock, and active are editable **directly in the list**, without opening a product
  (FR-022).
- The search box finds products by part of a name (FR-023).
- Products are labelled by name, not as *Product object (1)* (FR-010).
- Unticking **active** removes a product from `GET /api/products/` while its admin record remains
  (FR-024).

**Known gap, confirm it rather than be surprised by it**: set a price of `0` in the admin. It will
be accepted — the `price > 0` rule lives in the domain entity, and the admin binds straight to the
ORM model, bypassing it. Then call `GET /api/products/`. Because the repository validates on
mapping every row to an entity, that one bad row makes the **whole listing** fail, not just that
product. Set the price back to a valid value to recover. This is research D8 and data-model.md's
"where the model is stricter" note, seen live; closing it needs a `CheckConstraint` on price or an
admin `ModelForm`.

---

## Scenario 8 — Reproducible schema from nothing (SC-010)

```bash
docker compose down -v && docker compose up -d    # destroys the volume; recreates empty
python manage.py migrate
python manage.py test
```

Expect migrations to apply cleanly against an empty database with no manual steps, and the suite to
pass. This is the Definition-of-Done criterion the source named: *migrations run clean from zero.*

> `down -v` deletes the named volume and every product you created above. That is the point of the
> check — but do not run it against anything you want to keep.

---

## Before calling this done

- [ ] `python manage.py test` passes
- [ ] `scripts/check_architecture.sh` reports `Architecture boundaries OK.`
- [ ] `ruff format .` and `ruff check --fix .` are clean
- [ ] `sqlmigrate` shows the `CHECK ("stock" >= 0)` clause
- [ ] The migration file is committed alongside the model
- [ ] A price of `0` returns 422 and stores nothing
- [ ] `"12.345"` is refused rather than rounded
- [ ] Prices are JSON strings in every response
- [ ] An inactive product and a non-existent one both return a 404 that looks the same
- [ ] **FR-025 is still open and this feature is not deployed.** Writes have no authentication;
      anyone who can reach the API can rewrite prices or delete the catalog. Local only.
