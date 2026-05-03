# Backend API Notes

## Scope covered

This backend package currently provides:

- a FastAPI service/container named `backend`
- backend-local DB helper modules in `campx/api/`
- DB-backed CRUD for `customers`
- DB-backed simulation listing and creation
- DB-backed DS artifact import and retrieval
- `GET /model/state` for LinUCB inspection
- `POST /decide` in preview and live modes
- `POST /feedback` with reward calculation and model-state persistence
- generated Swagger docs at `/docs` and OpenAPI JSON at `/openapi.json`

## Current public routes

Supporting metadata endpoints:

- `GET /health`
- `GET /assumptions`
- `GET /api-structure`

Customer endpoints:

- `GET /customers`
- `GET /customers/{customer_id}`
- `POST /customers`
- `PUT /customers/{customer_id}`
- `DELETE /customers/{customer_id}`

Reference endpoints:

- `GET /actions`

Simulation endpoints:

- `GET /simulations`
- `POST /simulations`
- `PUT /simulations/{simulation_id}/complete`

Interaction and model endpoints:

- `GET /model/state?simulation_id=...`
- `POST /decide?simulation_id=...&customer_id=...&preview=true`
- `POST /decide?simulation_id=...&customer_id=...`
- `POST /feedback`

Metrics endpoint:

- `GET /metrics?simulation_id=...`

DS artifact endpoints:

- `POST /ds/artifacts`
- `GET /ds/artifacts/{simulation_id}`
- `GET /ds/artifacts/{simulation_id}/{artifact_name}`

## Response-shape conventions currently implemented

- `GET /customers` returns a raw array, not an `{items, count}` envelope
- `GET /simulations` returns a raw array, not an `{items, count}` envelope
- `GET /customers/{customer_id}` returns the richer detail shape with nested `rfm`, `interactions`, and optional `latents`
- `POST /simulations` returns the simulation record shape used by the backend and frontend contract
- `POST /decide` returns either:
  - an array of per-action scores in preview mode, or
  - `{interaction_id, recommended_action, scores}` in live mode
- `POST /feedback` returns `{interaction_id, reward, observed_at, model_updated}`
- `POST /ds/artifacts` returns counts for imported customers, actions, interactions, model-state rows, and stored generated artifacts.

## DB integration choices

- `db/1_schema.sql`, `db/2_indexes.sql`, `db/3_initial_insert.sql`, `db/4_views.sql`, and `db/5_stored_procedures.sql` are treated as the DB source of truth.
- The backend uses `campx/api/SQLHandler.py` and `campx/api/db_interactions.py` directly so the API container can run independently of older ETL layouts.
- Local scripts load `campx/.env`, and host-side DB access remaps compose-internal `db:5432` to `localhost:5434` when needed.
- `view_simulation_summary` is the main read source for simulation listing.
- `sp_upsert_customer`, `sp_log_interaction`, and `sp_submit_feedback` are the main write paths used by the API.
- `simulation_artifacts` stores generated CSV-style DS outputs as JSON/text payloads keyed by `simulation_id`.

## Model and interaction assumptions

- `POST /decide` no longer expects the caller to choose an action. The backend scores all actions and picks the top one in live mode.
- LinUCB state is reconstructed from observed interactions plus action metadata when serving `/model/state` and `/decide`.
- `interactions.context_vector` is stored as float64 binary feature bytes so the feedback path can reproduce the learning update.
- `POST /feedback` computes realized reward through the stored procedure and then persists updated `model_state` for the affected action.
- `POST /feedback` is only for pending interactions created by `POST /decide`; imported DS experiment interactions already include observed outcomes and will return 409 if submitted again.
- The current `/model/state` path uses customer features available in the live DB to derive scaling, because the DB schema does not store the richer DS-side feature-transform metadata.

## What is still incomplete

- `GET /metrics` is still only the lightweight aggregate payload, not the full dashboard payload required by `campx/app/backend_requirements.md`.
- `POST /simulations` still creates the DB record only. It does not yet launch Prefect/orchestration.
- Baseline-series data for the full analytics contract is not yet exposed from the DB-backed API.

## Operational note

If PostgreSQL was already initialized with a persistent Docker volume, editing the SQL files in `campx/db/` does not automatically update the live database objects. Stored procedures and indexes must be re-applied manually, or the DB volume must be recreated.
