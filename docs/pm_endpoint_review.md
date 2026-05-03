# PM Endpoint Review

This note reflects the current state of the repo after the latest backend, DB,
 and DS merges.

Checked against:

- `campx/app/backend_requirements.md`
- `campx/api/main.py`
- `campx/api/crud.py`
- frontend pages in `campx/app/pages/`

Validation done:

- `python3 -m compileall campx` passed
- `docker compose up --build` worked
- backend docs opened at `/docs`
- frontend opened at `:8501`
- pgAdmin opened at `:5050`

---

## Current Endpoint Status

| Endpoint | Status | Notes |
|---|---|---|
| `GET /simulations` | Done | Returns simulation summaries as a raw array. |
| `POST /simulations` | Partial | Creation route is finalized, but it still only creates the DB record. No orchestration trigger yet. |
| `GET /metrics` | Partial | Exists, but only returns lightweight totals. Not enough for the Interaction and Analytics pages. |
| `GET /customers` | Done | Returns a raw array and is usable for filtering/explorer use. |
| `GET /customers/{customer_id}` | Done | Returns nested `rfm`, interactions, and optional `latents` with `debug=true`. |
| `GET /model/state` | Partial | Exists and supports the Model page, but still needs full end-to-end validation. |
| `POST /decide` | Partial | Preview and live modes exist. Needs validation with the real frontend flow. |
| `POST /feedback` | Done | Feedback path is implemented and updates model state. |

---

## Page Readiness

### Create Simulation

Depends on:

- `GET /simulations`
- `POST /simulations`

Status:

- mostly ready
- main gap is that creation does not trigger orchestration yet

### Interaction

Depends on:

- `GET /simulations`
- `GET /metrics`

Status:

- blocked by `GET /metrics`

Still missing from metrics:

- `rounds_completed`
- `cumulative_reward`
- `avg_reward_per_round`
- `pending_observations`
- `cumulative_reward_series`
- `recent_interactions`

### Analytics

Depends on:

- `GET /simulations`
- `GET /metrics`
- optionally `GET /customers`

Status:

- blocked by `GET /metrics`

Still missing from metrics:

- `conversion_by_action`
- `action_distribution`
- `cumulative_reward_series`
- summary fields used in the page tiles

### Model

Depends on:

- `GET /simulations`
- `GET /model/state`
- `POST /decide?preview=true`

Status:

- route coverage is there
- needs live validation, not more route design

---

## What Changed Recently

### Backend

The backend is much more complete than before.

Main improvements:

- `GET /model/state` added
- `POST /decide` now supports preview and live behavior
- `GET /customers/{customer_id}` now returns richer detail
- validation is stricter
- error handling is cleaner

### DB

Main improvements:

- simulation summaries come from `view_simulation_summary`
- customer listing uses `view_customer_with_latents`
- writes use stored procedures

### DS

Main improvements:

- repeatable workflow script exists
- final output generation exists
- output artifacts are available

### Architecture

The old `campx/etl/` package was removed.

The active shared DB helper layer now lives under:

- `campx/api/SQLHandler.py`
- `campx/api/db_interactions.py`

---

## PM Tasks

### `#68` Design the complete list of required API endpoints and map each one to product functionality

What exists now:

- endpoint list
- route-to-page mapping
- implementation check against the live backend

What is still open:

- final `GET /metrics` shape
- final confirmation that Model-page behavior is good enough

### `#69` Share endpoint specifications with backend and frontend developers in a structured format

What exists now:

- detailed contract in `campx/app/backend_requirements.md`
- current implementation review in this file

What is still open:

- update the detailed contract where backend behavior changed
- publish the final version cleanly in docs

### `#70` Review the UI needs with the frontend developer and suggest built-in Streamlit components

Current frontend uses built-in Streamlit components appropriately:

- forms
- text inputs
- number inputs
- sliders
- selectboxes
- metrics
- dataframes
- toggles
- expanders


### `#71` Ensure the DS, Backend, Frontend, and Orchestration roles are aligned on data flow and dependencies

What is aligned:

- DB, DS, and backend are much closer now
- backend exposes the main customer/simulation/model/feedback routes

What is not aligned yet:

- frontend still uses mocks
- `GET /metrics` is not enough for the real frontend
- orchestration still does not drive the actual run lifecycle

### `#72` Track blockers and make decisions on scope if some features need simplification

Current blockers:

- frontend still on mocks
- `GET /metrics` incomplete
- orchestration not ready

Most realistic simplification:

- keep simulation creation, metrics, customer detail, model state, and feedback in scope
- treat orchestration-triggered run automation as stretch unless it is finished cleanly

---

## What Is Left For This Milestone

The main remaining work is:

1. Replace frontend mocks with live backend calls.
2. Expand `GET /metrics` to match the dashboard pages.
3. Decide whether orchestration is required for milestone sign-off or documented as stretch scope.
4. Run live frontend/backend smoke tests page by page.
