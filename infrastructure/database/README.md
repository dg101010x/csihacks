# Database (Section 20)

- **Local dev**: SQLite by default (`DATABASE_URL` unset), file at `apps/api/relief_dev.db` (gitignored).
- **Postgres**: set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname` — every module's SQL store (relief_ledger, relief_obligations, relief_consumer_constitution, relief_workflow_worker, relief_audit) works against either engine unchanged, since none of them use SQLite-specific SQL. `infrastructure/deployment/docker-compose.yml` runs Postgres 16 this way.
- **Schema creation**: `apps/api/app/db.py`'s `create_all_tables()` calls `Base.metadata.create_all()` for every module's independent `Base` against one shared engine — each module owns its own tables (Section 29), apps/api is the one place that knows about all of them.
- **Not yet built**: real migrations (Alembic or similar). `create_all_tables()` only adds missing tables; it never alters an existing one, so changing a model's schema after data exists needs a manual migration today. Tracked as a real gap before this is production-safe against a database that already has rows in it.
