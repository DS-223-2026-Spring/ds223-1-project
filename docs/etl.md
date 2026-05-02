# ETL & Shared Data Access

**Owner:** Shared between DB, DS, and Backend

---

## Purpose

The `campx/etl/` package contains shared database access helpers that let
multiple services talk to PostgreSQL without re-implementing connection logic.

In practice, it acts as the bridge layer between:

- the PostgreSQL schema in `campx/db/`
- the DS workflow in `campx/ds/`
- the FastAPI service in `campx/api/`

---

## Current role in the project

The ETL package is intentionally small. It provides:

- `SQLHandler.py` for database connection management
- `db_interactions.py` for reusable database read/write helpers

These helpers are mounted into the DS and backend containers through
`docker-compose.yml`, which keeps the services aligned on the same DB access
pattern.

---

## Files

### `campx/etl/SQLHandler.py`

Shared low-level PostgreSQL connection helper used by multiple services.

### `campx/etl/db_interactions.py`

Shared helper layer for common DB operations such as:

- customer retrieval
- interaction writes
- simulation writes
- model-state persistence

---

## Service relationship

### Database

Owns the schema, views, stored procedures, and table definitions.

### ETL / shared helper layer

Owns reusable Python-side DB access patterns.

### DS

Uses the helper layer to persist generated customers, interactions, and model
state.

### Backend

Uses the same access pattern to expose DB-backed API endpoints.

---

## Current implementation note

Recent backend changes moved more logic into database-side views and stored
procedures, especially for:

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
