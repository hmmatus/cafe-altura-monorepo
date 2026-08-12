# Café Altura — Backend

Django + DRF API built on clean architecture, so the business logic stays independent of the
framework and the database.

## Stack

| | |
|---|---|
| Python | 3.12 |
| Django | 6.0.7 |
| Django REST Framework | 3.17.1 |
| Database | PostgreSQL 16 (`psycopg` 3) |
| Config | `django-environ` |
| Lint / format | ruff |
| Git hooks | pre-commit |

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements-dev.txt   # includes requirements.txt
pre-commit install                    # installs BOTH pre-commit and pre-push hooks
```

`pre-commit install` is required for every clone — git hooks are not tracked by git.

### Database

The dev database runs in Docker on host port **5433** (5432 is left to any local Postgres):

```bash
docker run --name cafe-altura-db \
  -e POSTGRES_USER=cafe \
  -e POSTGRES_PASSWORD=cafe \
  -e POSTGRES_DB=cafe_altura \
  -p 5433:5432 \
  -d postgres:16
```

Data lives in the container's writable layer — it survives `docker stop`/`start` but is lost
on `docker rm`. Add `-v cafe-altura-pgdata:/var/lib/postgresql/data` to make it durable.

### Environment

Create a `.env` in the project root (never commit it):

```dotenv
SECRET_KEY=<generate one>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://cafe:cafe@localhost:5433/cafe_altura
```

## Commands

The virtualenv is not auto-activated — activate it or prefix with `.venv/bin/`.

```bash
python manage.py migrate
python manage.py runserver
python manage.py test
python manage.py createsuperuser

ruff format .           # format
ruff check --fix .      # lint
```

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health/` | Liveness/readiness; 503 when a dependency is down |
| `GET` | `/api/products/` | Active products, newest first |
| `POST` | `/api/products/` | Create a product |
| `GET` | `/api/products/<id>/` | One active product |
| `PUT` / `PATCH` | `/api/products/<id>/` | Replace / partially update; reaches inactive products |
| `DELETE` | `/api/products/<id>/` | Delete permanently |

Two things a consumer will otherwise get wrong:

- **Prices are JSON strings** (`"12.50"`, not `12.50`). Parse with a decimal type — parsing into
  a float reintroduces the rounding drift that exact decimal storage exists to prevent.
- **The product listing is unpaginated** and returns a bare array. Adding pagination later turns
  that array into an object, which breaks clients written against the current shape.

Status codes split by *kind* of failure: a malformed request shape is `400` with DRF's
field-keyed body, while a broken business rule (price at or below zero, over-precise price,
negative stock) is `422` with a `detail` message. An inactive product and one that never existed
both return an identical `404`.

> ⚠️ **The product write operations have no authentication.** Anyone who can reach the service can
> rewrite prices or delete the catalog. This is deliberate for local development (FR-025) and is a
> release blocker — do not deploy until writes are restricted to administrators.

Full contract: [`specs/001-product-catalog/contracts/products-api.yaml`](specs/001-product-catalog/contracts/products-api.yaml).

## Architecture

Dependencies point inward. `domain/` and `application/` must survive a swap of Django, DRF,
or PostgreSQL without changes.

```
interface/  ──┐
              ├──> application/ ──> domain/
infrastructure/ ┘
```

```
config/            Django wiring only — settings, urls, container.py
domain/            entities, value objects, domain exceptions — ZERO framework imports
application/       use cases and ABC ports (repositories, gateways) — ZERO framework imports
infrastructure/    Django ORM models, repository implementations, external clients
interface/         DRF serializers, views, urls — no business logic, no `.objects`
```

Rules:

- The Django model is **not** the domain entity. Repositories map between them and return
  entities, never a `QuerySet`.
- Use cases receive ports through `__init__`. Concrete classes are named only in
  `config/container.py`.
- Domain exceptions are domain classes; the view maps them to HTTP status codes.
- `domain/` and `application/` are plain Python packages, not Django apps. Only
  `infrastructure.db` belongs in `INSTALLED_APPS`.

New endpoints are built inward-out: domain → port → use case → model → repository →
container → view → route.

## Git Hooks

Managed by `pre-commit`, configured in `.pre-commit-config.yaml`.

**On `git commit`** — trailing whitespace, end-of-file, YAML/TOML syntax, large files, merge
conflict markers, private-key detection, then `ruff format` and `ruff check --fix`.

**On `git push`**

1. `scripts/check_architecture.sh` — fails the push on a framework import inside `domain/`
   or `application/`, an inner layer importing an outer one, or `.objects` under `interface/`.
2. `python manage.py test`.

Run them manually:

```bash
pre-commit run --all-files                      # commit-stage hooks
pre-commit run --hook-stage pre-push --all-files # push-stage hooks
```

The push-stage tests need the Postgres container running — `manage.py test` creates a test
database on 5433. Use `git push --no-verify` to bypass in an emergency.

## Claude Code

`CLAUDE.md` holds the project rules. Two skills encode the architecture:

- `.claude/skills/django-project-structure/` — layout and layer boundaries
- `.claude/skills/django-endpoint-creator/` — ordered recipe for a new endpoint

The `python-dev` agent (`.claude/agents/python-dev.md`) implements backend work under those
rules.
