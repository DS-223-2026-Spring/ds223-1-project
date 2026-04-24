# Backend API Notes

## Scope covered

This backend package now provides:

- a FastAPI service/container named `back`
- a clean package layout under `backend/app`
- dummy CRUD for `customers`
- placeholder database-backed endpoints for `actions`, `simulations`, `decide`, `feedback`, and `metrics`
- generated Swagger docs at `/docs` and OpenAPI JSON at `/openapi.json`

## Resource names and API structure

The current backend contract uses these public resource names:

- `customers`
- `actions`
- `simulations`
- `interactions`
- `metrics`

Supporting metadata endpoints:

- `GET /health`
- `GET /assumptions`
- `GET /api-structure`

Primary CRUD surface for milestone work:

- `GET /customers`
- `GET /customers/{customer_id}`
- `POST /customers`
- `PUT /customers/{customer_id}`
- `DELETE /customers/{customer_id}`

Supporting placeholder endpoints:

- `GET /actions`
- `GET /simulations`
- `POST /simulations`
- `PUT /simulations/{simulation_id}/complete`
- `POST /decide`
- `POST /feedback`
- `GET /metrics?simulation_id=...`

## DB and ETL integration choices

- `db/1_schema.sql`, `db/2_indexes.sql`, and `db/3_initial_insert.sql` were treated as the source of truth for table names and seeded actions.
- `etl/SQLHandler.py` and `etl/db_interactions.py` were copied into backend-local modules so the backend container can import the shared DB helper layer without modifying `etl/`.
- The backend implementation reads `backend/.env` for local verification and uses the same file from `docker-compose.yml`.

## Assumptions

- `customers` is the main CRUD resource because the existing schema and shared helper functions already support reads and writes across `customers` and `customer_latents`.
- List endpoints currently return an `{items, count}` envelope for consistency inside the backend service.
- `decide` is a placeholder write path; callers still provide `action_id` until the DS-owned LinUCB selection logic is wired in.
- Simulation creation currently writes a DB record only; orchestration-triggered execution remains a follow-up.
- Host-side DB checks translate the compose-internal `db:5432` settings to `localhost:5434` when scripts are run outside Docker.

## Pending dependencies

- PM/frontend confirmation on whether list endpoints should stay wrapped as `{items, count}` or switch to raw arrays before the frontend stops using mocks.
- PM/frontend confirmation on whether a dedicated `POST /simulate` alias is still required for M3, or whether `POST /simulations` is acceptable.
- DS integration behind `/decide` for automatic action selection and model-state updates.
- Orchestration wiring so simulation creation can launch the Prefect flow asynchronously.
- Shared agreement on naming: frontend requirements still mention a backend service called `api`, while docker-compose now runs `back`. Compose now injects `API_URL=http://back:8000` for runtime compatibility.
