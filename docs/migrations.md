# Database Migrations

Tastebuds uses Alembic for schema changes. Configuration lives in
`api/alembic.ini`, and `api/alembic/env.py` reads `DATABASE_URL` from the
settings module.

## Workflow (Docker-first)
1. Update models and metadata in `api/app/models` and `api/app/db/base.py`.
2. Generate a migration:
   `docker compose exec api alembic revision --autogenerate -m "add ..."`
3. Review the generated file for indexes, constraints, and ordering.
4. Apply migrations: `./scripts/dev.sh migrate` (runs `alembic upgrade head`).

Local (no Docker):
- `cd api && alembic upgrade head`

## Backfill patterns
- Add new nullable columns first, backfill data, then enforce NOT NULL in a
  follow-up migration.
- Prefer set-based SQL via `op.execute` for backfills; avoid ORM row loops.
- For large tables, batch updates or run a separate backfill script to keep
  migrations fast and predictable.
- For new non-null columns, use a temporary `server_default` and remove it
  after backfill if needed.
- If a change depends on extensions or database-side configs (ex: `unaccent` or
  text search configs), create them in the same migration before any functions
  or triggers reference them.

## Rollback guidance
- Always implement `downgrade` for schema changes.
- For destructive changes, document that downgrade is lossy and prefer
  roll-forward.
- Roll back one step: `docker compose exec api alembic downgrade -1`.
- Take a database snapshot before data-destructive migrations.
