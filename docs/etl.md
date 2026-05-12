# ETL & Shared Data Access

**Owner:** Shared between DB, DS, and Backend

---

## Purpose

The project originally used a separate `campx/etl/` package for shared database
access helpers. In the current architecture, that separate package has been
removed and the active DB helper layer now lives under `campx/api/`.

In practice, the shared data-access layer still acts as the bridge between:

- the PostgreSQL schema in `campx/db/`
- the DS workflow in `campx/ds/`
- the FastAPI service in `campx/api/`

---

## Current role in the project

The active shared helper layer is intentionally small. It provides:

- `campx/api/SQLHandler.py` for database connection management
- `campx/api/db_interactions.py` for reusable database read/write helpers

These helpers are mounted into the DS and backend containers through
`docker-compose.yml`, which keeps the services aligned on the same DB access
pattern.

---

## Files

### `campx/api/SQLHandler.py`

Shared low-level PostgreSQL connection helper used by multiple services.

### `campx/api/db_interactions.py`

Shared helper layer for common DB operations such as:

- customer retrieval
- interaction writes
- simulation writes
- model-state persistence

---

## Service relationship

### Database

Owns the schema, views, stored procedures, and table definitions.

### Shared helper layer

Owns reusable Python-side DB access patterns.

### DS

Uses the helper layer to persist generated customers, interactions, and model
state.

Generated DS data is created as a complete seeded artifact bundle first. The
DB path then reads the generated CSV directory and bulk loads the relational
tables:

- actions are upserted as one batch
- customers and customer latents are inserted as table batches
- generated interactions are inserted with their already observed outcomes as
  one interaction batch
- generated model-state rows are upserted as one batch

This is the initialization/import path used by:

```bash
python -m campx.ds.run_workflow --storage db
```

The in-process simulation runner also computes its rounds sequentially in
memory, then bulk inserts the generated interaction batch and final model
state. The live `/decide` and `/feedback` flow still uses the stored procedures
one interaction at a time, because those requests represent real online
decisions and delayed outcomes rather than generated initialization data.

### Backend

Uses the same access pattern to expose DB-backed API endpoints.

---

## Current implementation note

Recent backend changes both:

- removed the old `campx/etl/` package
- moved the active helper layer into `campx/api/`
- pushed more logic into database-side views and stored procedures

Especially for:

- simulation summaries
- customer upserts
- interaction logging
- feedback submission

So the shared ETL/helper layer is still important, but the project is now more
DB-driven than before.

---

## Run context

The full stack is started from the repository root:

```bash
docker compose up --build
```

This brings up:

- PostgreSQL
- pgAdmin
- backend
- frontend
- DS workflow container

The DS container currently runs its workflow and exits normally after writing
artifacts, while the backend and frontend remain live.
