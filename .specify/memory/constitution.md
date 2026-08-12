<!--
Sync Impact Report
Version change: (unversioned template) → 1.0.0
Bump rationale: Initial ratification. The file previously contained only unfilled
template placeholders; this is the first concrete governance document.
Modified principles:
  - [PRINCIPLE_1_NAME] → I. Clean Architecture Boundaries (NON-NEGOTIABLE)
  - [PRINCIPLE_2_NAME] → II. Build Inward-Out
  - [PRINCIPLE_3_NAME] → III. Test-First
  - [PRINCIPLE_4_NAME] → IV. Explicit Contracts at the Edge
  - [PRINCIPLE_5_NAME] → V. Configuration Through Environment
Added sections:
  - Technology & Environment Constraints (was [SECTION_2_NAME])
  - Development Workflow & Quality Gates (was [SECTION_3_NAME])
Removed sections: none
Follow-up TODOs: none
-->

# Café Altura Backend Constitution

## Core Principles

### I. Clean Architecture Boundaries (NON-NEGOTIABLE)

Dependencies MUST point inward: `interface/` and `infrastructure/` depend on `application/`,
which depends on `domain/`. `domain/` depends on nothing but the standard library.

- `domain/` and `application/` MUST NOT import `django`, `rest_framework`, or any concrete
  adapter. They MUST NOT import `infrastructure/`, `interface/`, or `config/`.
- `domain/` MUST NOT import `application/`.
- `interface/` MUST NOT touch the ORM. No `.objects` access outside `infrastructure/`.
- A Django ORM model is NOT a domain entity. Repositories translate between the persistence
  shape and the entity shape.
- Concrete implementations are named in exactly one place: `config/container.py`.
- Business contexts (`orders`, `products`, `customers`) name directories; technical buckets
  (`utils`, `common`, `helpers`) MUST NOT.

Rationale: the business logic is the product; Django, DRF, and PostgreSQL are replaceable
details. A swap of any of them MUST leave `domain/` and `application/` unchanged.
`scripts/check_architecture.sh` enforces this mechanically on pre-push; violations block.

### II. Build Inward-Out

Features MUST be built in dependency order: domain entity → application port → use case →
persistence model and migration → repository adapter → container wiring → HTTP view and route.

- Ports (ABCs in `application/<context>/interfaces.py`) MUST declare only the methods the
  current use case calls. Speculative CRUD ports are forbidden (YAGNI).
- A use case is one class with one public `execute()`. Dependencies arrive through `__init__`.
- A use case MUST NOT accept or return `request`, `Response`, a serializer, or a JSON-shaped
  `dict`. It takes and returns DTOs or entities.

Rationale: each step depends only on steps above it, so each is testable alone. Writing the
view first inverts the dependency arrow and drags framework concerns inward.

### III. Test-First

Tests MUST be written before the implementation they cover, and MUST fail before they pass.

- Use-case tests MUST run without a database and without HTTP, using in-memory fakes that
  implement the port. A use-case test that needs `migrate` or `APIClient` is proof that logic
  leaked outward — the fix is to move the logic, not to widen the test.
- Repository tests use the real database and assert entity ↔ row round-trips.
- View tests use `APIClient` and assert status codes and payload shape only.
- `python manage.py test` MUST pass before any push. The pre-push hook enforces this.

Rationale: layer-appropriate tests are the executable proof that the boundaries in Principle I
actually hold. Fast domain tests stay fast only if nothing framework-bound leaks into them.

### IV. Explicit Contracts at the Edge

The boundary between HTTP and the application MUST be explicit and mechanical.

- Domain errors are domain classes (`OrderNotFound`, `OrderInvalid`). They MUST NOT carry HTTP
  status codes, and MUST NOT be `Http404` or DRF exceptions.
- The view owns the mapping: `*NotFound` → 404, `*Invalid` / broken invariant → 422,
  `*Conflict` / duplicate → 409, `NotAllowed` → 403, serializer failure → 400.
- Serializers validate request shape and shape responses. A `validate_*` method MUST NOT apply
  a business rule; invariants belong on the entity.
- Views contain no business logic and no queries.

Rationale: business meaning and transport encoding are separate concerns. Keeping status codes
out of the domain is what lets the same use case serve HTTP, a CLI, or a worker unchanged.

### V. Configuration Through Environment

All configuration MUST be read from the environment via `django-environ`; none may be
hardcoded.

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL` come from the environment or `.env`.
- `.env` MUST NOT be committed. Secrets MUST NOT appear in source, tests, or fixtures.
  The `detect-private-key` pre-commit hook is a backstop, not a substitute for care.
- The database is PostgreSQL, configured through `DATABASE_URL` / `env.db()`. The SQLite
  default MUST NOT be relied upon, including in tests.

Rationale: the same artifact must run in every environment, and a leaked credential is not
revocable by a later commit.

## Technology & Environment Constraints

- Python 3.12, Django 6.0.x, Django REST Framework 3.17.x, PostgreSQL 16 via `psycopg` 3.
- The in-repo `.venv/` is not auto-activated. Commands MUST be run with the venv activated or
  prefixed with `.venv/bin/`.
- Dependencies MUST be pinned with exact `==` versions. Runtime deps go in `requirements.txt`;
  tooling goes in `requirements-dev.txt`, which includes the former.
- The development database runs in Docker on host port **5433**, leaving 5432 to any local
  PostgreSQL belonging to another account on the machine.
- `pre-commit install` is required on every clone; git hooks are not tracked by git. It installs
  both the `pre-commit` and `pre-push` hook types.
- Formatting and linting are ruff's job: `ruff format .` and `ruff check --fix .`, line length
  100, target `py312`. Migrations are excluded from linting.

## Development Workflow & Quality Gates

Two gates run automatically and MUST NOT be bypassed with `--no-verify`:

**On commit** — trailing whitespace, end-of-file, YAML/TOML validity, large-file and
merge-conflict checks, private-key detection, `ruff-format`, `ruff check --fix`.

**On push** — `scripts/check_architecture.sh` (Principle I) and `python manage.py test`
(Principle III).

Additional expectations:

- Work happens on a branch; `main` is not committed to directly.
- Any change adding or altering an endpoint MUST follow the ordered recipe in
  `.claude/skills/django-endpoint-creator/SKILL.md`.
- Any change adding a file MUST place it per `.claude/skills/django-project-structure/SKILL.md`.
- Model changes MUST ship with their generated migration in the same commit.
- A red flag from the endpoint skill (view written first, `.objects` under `interface/`, a use
  case importing `rest_framework`, a concrete repository named outside `config/container.py`)
  is a stop-and-rebuild condition, not a review comment to negotiate.

## Governance

This constitution supersedes other practices, conventions, and habits in this repository. Where
`CLAUDE.md`, a skill file, or a README disagrees with it, this document wins and the other file
MUST be corrected.

**Amendment procedure.** Amendments MUST be proposed as a change to this file, MUST state the
rationale and the version bump in the Sync Impact Report, and MUST include a migration note when
existing code would become non-compliant. An amendment that relaxes a NON-NEGOTIABLE principle
requires an explicit written justification of what replaces the guarantee being removed.

**Versioning policy.** Semantic versioning applies to governance:

- **MAJOR** — a principle is removed or redefined in a backward-incompatible way.
- **MINOR** — a principle or section is added, or guidance is materially expanded.
- **PATCH** — clarification, wording, or typo fixes with no change in obligation.

**Compliance review.** Every pull request MUST be reviewed against these principles, and the
automated gates above MUST be green. Complexity that appears to violate a principle MUST be
justified in the pull request description or removed; "it was faster" is not a justification.
Runtime development guidance lives in `CLAUDE.md` and the skills under `.claude/skills/`.

**Version**: 1.0.0 | **Ratified**: 2026-08-11 | **Last Amended**: 2026-08-11
