# CLAUDE.md

Guidance for Claude Code working in this repository.

## Status

The Django scaffold exists. `manage.py`, `config/` (settings, urls, container), the four
architecture layers, `tests/`, and `scripts/` are all in place. Two contexts are wired end to
end: `health` (`GET /api/health/`) and `catalog` (`/api/products/`, full CRUD). Build within the
existing layout rather than creating a new one.

`infrastructure.db` is the only Django app in `INSTALLED_APPS`; `domain/` and `application/` are
plain Python packages. The catalog's write endpoints deliberately carry no authentication
(FR-025) — that is a release blocker, tracked in `specs/001-product-catalog/`.

Governance for this repo lives in `.specify/memory/constitution.md`. Where this file and the
constitution disagree, the constitution wins and this file must be corrected.

## Stack

- Python 3.12 (`.venv/`, Python 3.12.10)
- Django 6.0.7
- Django REST Framework 3.17.1
- PostgreSQL 16 via `psycopg` 3.3.4 (binary wheels included)
- `django-environ` 0.14.0 for config — settings read from environment / `.env`, never hardcoded
- ruff 0.14.4 for lint and format, pre-commit 4.4.0 for git hooks

## Layout

```
config/           # Django wiring only — settings.py, urls.py, container.py
domain/           # <context>/ — entities.py, exceptions.py. Zero framework imports.
application/      # <context>/ — interfaces.py (ABC ports), services.py, dtos.py. Zero framework imports.
infrastructure/   # db/ (apps.py, admin.py, models/, repositories/, migrations/, probes), external/
interface/        # api/<context>/ — serializers.py, views.py, urls.py
tests/            # mirrors the layer it tests: tests/application/..., tests/interface/api/...
scripts/          # check_architecture.sh — the pre-push boundary check
```

`<context>` is a business area (`orders`, `products`, `customers`) — never a technical grouping
(`utils`, `common`, `helpers`).

## Commands

Always use the in-repo virtualenv; it is not auto-activated.

```bash
source .venv/bin/activate          # or prefix commands with .venv/bin/
pip install -r requirements-dev.txt   # includes requirements.txt
pre-commit install                    # installs BOTH pre-commit and pre-push hooks

python manage.py runserver
python manage.py migrate
python manage.py makemigrations
python manage.py test
python manage.py createsuperuser

ruff format .                      # format
ruff check --fix .                 # lint
```

`pre-commit install` is required on every clone — git hooks are not tracked by git.

Pinning: `requirements.txt` uses exact `==` pins for runtime deps, `requirements-dev.txt` for
tooling. Keep new dependencies pinned, and regenerate with `pip freeze` after installs.

### Database

The dev database runs in Docker on host port **5433** (5432 is left to any local Postgres
belonging to another macOS account on the machine). See README.md for the exact invocation.

## Architecture Rule (non-negotiable)

This project follows **clean architecture**. Layers are separated so the business logic is
portable — if Django, DRF, or PostgreSQL is swapped out, `domain/` and `application/` must
survive unchanged.

```
interface/  ──┐
              ├──> application/ ──> domain/
infrastructure/ ┘
```

| Layer | May import | Must NOT contain |
|---|---|---|
| `domain` | stdlib only | `django`, `rest_framework`, ORM, HTTP, SQL |
| `application` | `domain`, stdlib, `abc` | `django`, `rest_framework`, concrete repos |
| `infrastructure` | `application`, `domain`, django | business rules, HTTP status codes |
| `interface` | `application`, `domain`, django, DRF | business rules, ORM queries, `.objects` |

The ORM model is not the entity — repositories translate between them. `config/container.py`
is the only module allowed to name concrete classes.

Before writing backend code, read the skills that define this:

- `.claude/skills/django-project-structure/SKILL.md` — layout and layer boundaries
- `.claude/skills/django-endpoint-creator/SKILL.md` — ordered recipe for any endpoint

Use the `python-dev` agent for backend implementation work; it enforces these rules.

## Quality Gates

Both run automatically. Do not bypass with `--no-verify`.

- **pre-commit** — trailing whitespace, end-of-file, YAML/TOML validity, large-file and
  merge-conflict checks, private-key detection, `ruff-format`, `ruff check --fix`.
- **pre-push** — `scripts/check_architecture.sh` (layer boundaries) and `manage.py test`.

Run the boundary check by hand any time:

```bash
scripts/check_architecture.sh
```

## Conventions

- Build inward-out: domain → port → use case → model/migration → repository → container → view.
  Writing `views.py` first is a stop-and-rebuild condition.
- Tests come first. Use-case tests need no database and no HTTP — instantiate the use case with
  an in-memory fake implementing the port. A use-case test that needs `migrate` or `APIClient`
  means logic leaked outward.
- Domain exceptions are domain classes (`OrderNotFound`), never `Http404` or DRF exceptions.
  The view owns the status mapping: `*NotFound` → 404, `*Invalid` → 422, `*Conflict` → 409,
  `NotAllowed` → 403, serializer failure → 400.
- Config through `django-environ`: `env = environ.Env()`, values from `.env`. `.env` is never
  committed; `.gitignore` already covers it along with `.venv/`, `__pycache__/`, `*.pyc`.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL` come from the environment. No
  secrets in source, tests, or fixtures.
- Database is PostgreSQL — use `env.db()` / `DATABASE_URL` rather than the sqlite default.
- ruff config lives in `pyproject.toml`: line length 100, target `py312`, migrations excluded.
- Model changes ship with their generated migration in the same commit.
- Work on a branch; do not commit directly to `main`.
