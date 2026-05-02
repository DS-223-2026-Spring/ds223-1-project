# PM Endpoint Review

This note compares three things:

1. the frontend/backend contract described in `campx/app/backend_requirements.md`
2. the current FastAPI implementation in `campx/api/main.py`
3. the actual frontend page expectations in `campx/app/`

It is intended to support PM tasks `#68`, `#69`, `#70`, `#71`, and `#72`.

Current validation context:

- Python compile check passed: `python3 -m compileall campx`
- Full stack startup check passed with `docker compose up --build`
- Backend Swagger served successfully at `/docs`
- Streamlit served successfully at port `8501`
- pgAdmin served successfully at port `5050`
- DS container executed and exited normally after writing artifacts

---

## Status Key

- `Aligned`: endpoint exists and broadly matches the current UI need
- `Partial`: endpoint exists but name, shape, or behavior does not fully match
- `Missing`: frontend expects it, backend does not provide it
- `Optional`: useful, but not required for the minimum demo path

---

## Endpoint Status Table

| Endpoint | Frontend / PM expectation | Current backend state | Status | Notes |
|---|---|---|---|---|
| `GET /simulations` | List all runs for selectors and tables | Implemented | Aligned | Returns simulation summaries with `status`, `cumulative_reward`, and `rounds_completed` from `view_simulation_summary`. |
| `POST /simulate` | Create and trigger a simulation run | Not implemented under this exact name | Partial | Backend uses `POST /simulations` instead. PM must decide whether to keep only REST-style naming or add an alias. |
| `POST /simulations` | Backend alternative to simulation creation | Implemented | Partial | Works for record creation, but frontend spec currently expects `POST /simulate` and orchestration is not triggered yet. |
| `GET /metrics` | Return rich dashboard payload for Interaction and Analytics pages | Implemented with limited totals only | Partial | Current shape is too small for UI. Missing series data, pending counts, recent interactions, and per-action aggregates. |
| `GET /customers` | Return customer list | Implemented | Partial | Exists and is useful, but returns `{items, count}` envelope while frontend spec currently describes a raw array. |
| `GET /customers/{customer_id}` | Return one customer, optionally with debug latents and interactions | Implemented | Partial | Returns customer plus latents, but not the richer nested shape from the spec and does not support the documented `debug=true` behavior. |
| `GET /model/state` | Return theta matrix, pull counts, alpha, and model state metadata | Not implemented | Missing | Required if the Model page remains in scope. |
| `POST /decide` | Preview UCB scores or log a real decision | Implemented as placeholder write path | Partial | Logs a caller-supplied action via `sp_log_interaction`, but does not support preview mode or full per-action scoring response. |
| `POST /feedback` | Close an interaction when reward is observed | Implemented | Aligned | Uses `sp_submit_feedback`; good foundation for orchestration and pending-observation lifecycle. |

---

## Page-Level Dependency Check

### Create Simulation

Source:
- `campx/app/pages/1_create_simulation.py`

Needs:
- `GET /simulations`
- simulation creation endpoint

Assessment:
- `GET /simulations` is ready enough
- create flow is only partially ready because:
  - frontend expects `POST /simulate`
  - backend exposes `POST /simulations`
  - orchestration is not yet wired, so it only creates a DB record

### Interaction

Source:
- `campx/app/pages/2_interaction.py`

Needs:
- `GET /simulations`
- `GET /metrics?simulation_id=...`

Assessment:
- selector input is covered
- metrics payload is not sufficient yet

Missing for this page:
- `rounds_completed`
- `cumulative_reward`
- `avg_reward_per_round`
- `pending_observations`
- `cumulative_reward_series`
- `recent_interactions`

### Analytics

Source:
- `campx/app/pages/3_analytics.py`

Needs:
- `GET /simulations`
- `GET /metrics?simulation_id=...`
- optionally `GET /customers`

Assessment:
- `GET /simulations` is fine
- `GET /metrics` is still insufficient for charts and per-action summaries

Missing for this page:
- `conversion_by_action`
- `action_distribution`
- `cumulative_reward_series`
- top-level summary fields used by tiles

### Model

Source:
- `campx/app/pages/4_model.py`

Needs:
- `GET /simulations`
- `GET /model/state?simulation_id=...`
- `POST /decide?preview=true`

Assessment:
- only the selector dependency is currently satisfied
- this page is the least integrated page today

---

## What Improved After The Latest Merges

### DB / API Layer

The DB merge improved backend internals:

- customer listing now uses `view_customer_with_latents`
- simulation listing now uses `view_simulation_summary`
- customer create/update now uses `sp_upsert_customer`
- decision logging now uses `sp_log_interaction`
- feedback now uses `sp_submit_feedback`

This is a good structural improvement. It makes the backend more database-backed and reduces repeated SQL in Python.

### DS Layer

The DS merge improved reproducibility and deliverables:

- repeatable workflow script added
- final output generation added
- generated output artifacts committed
- modeling docs updated

This means the DS side is stronger, but these changes do not by themselves complete frontend integration.

---

## PM Decisions Still Needed

These are the most important unresolved PM decisions:

1. Should simulation creation use only `POST /simulations`, or should backend also expose `POST /simulate` as an alias for frontend compatibility?
2. Should list endpoints return raw arrays or `{items, count}` envelopes?
3. Is the Model page in final scope?
   - If yes, `GET /model/state` and preview `POST /decide` are required.
   - If no, those can be explicitly downgraded from must-have to stretch.
4. Is full orchestration required for the demo, or is “record creation plus documented limitation” acceptable?

---

## Current PM Read

### Strong areas

- DB foundation
- DS workflow and outputs
- simulation summary data
- feedback lifecycle foundation
- containerized stack startup
- backend Swagger availability

### Weak areas

- frontend-backend endpoint alignment
- metrics payload completeness
- model-state exposure
- preview decision scoring
- orchestration-triggered runs

---

## Recommended Next PM Actions

1. Freeze the public endpoint contract in one place.
2. Decide route naming and response envelope conventions immediately.
3. Mark Model page as either:
   - required, or
   - stretch scope
4. Define a minimum demo-safe integration target:
   - `GET /simulations`
   - simulation creation route
   - `GET /metrics` with full dashboard payload
   - `POST /feedback`
5. Document orchestration limitations honestly if full Prefect automation is not finished.

---

## PM Task Matrix

### `#68` Design the complete list of required API endpoints and map each one to product functionality

What this task means:
- define the public backend contract
- connect each endpoint to a concrete app behavior

Current status:
- `Partial to Strong`

Evidence:
- endpoint draft already exists in `campx/app/backend_requirements.md`
- current backend routes already cover much of the surface area
- this review now maps page needs to implemented routes

Still needed:
- freeze final naming
- freeze final response shapes
- decide whether Model page endpoints are in required scope

Recommended PM close-out:
- keep this review plus the frontend requirements doc as the basis
- produce one final endpoint table with `endpoint`, `used by`, `input`, `response`, `owner`, `status`

### `#69` Share endpoint specifications with backend and frontend developers in a structured format

What this task means:
- publish one source of truth that both backend and frontend follow

Current status:
- `Partial`

Evidence:
- contract details live in `campx/app/backend_requirements.md`
- backend assumptions live in `campx/api/API_NOTES.md`
- this PM review now summarizes actual implementation status

Still needed:
- consolidate into one PM-owned document
- remove ambiguity around naming and envelope choices

Recommended PM close-out:
- use this file as the review layer
- use the endpoint requirements document as the detailed contract
- update MkDocs later so the team has a published version

### `#70` Review the UI needs with the frontend developer and suggest built-in Streamlit components

What this task means:
- verify each page's data dependencies and UI widgets

Current status:
- `Strong`

Evidence:
- page implementations already show the UI contract:
  - Create Simulation
  - Interaction
  - Analytics
  - Model

Built-in Streamlit components already being used well:
- `st.form`
- `st.text_input`
- `st.number_input`
- `st.slider`
- `st.multiselect`
- `st.text_area`
- `st.selectbox`
- `st.metric`
- `st.dataframe`
- `st.toggle`
- `st.expander`
- `st.page_link`

Still needed:
- translate page-level needs into backend-ready data requirements
- decide whether the Model page is final-scope or stretch

### `#71` Ensure the DS, Backend, Frontend, and Orchestration roles are aligned on data flow and dependencies

What this task means:
- confirm who produces which data
- confirm who consumes it
- confirm what is still blocked

Current status:
- `Partial`

What is aligned:
- DB supports customer, simulation, interaction, and model-state persistence
- DS now has repeatable workflows and final outputs
- backend can read/write core entities

What is not yet aligned:
- frontend expects richer metrics than backend currently exposes
- frontend expects Model-page endpoints that backend does not yet provide
- simulation creation does not yet trigger orchestration
- preview scoring flow is not yet integrated with DS model state

Recommended PM close-out:
- create a small dependency map:
  - DB -> backend summaries and writes
  - DS -> model state and final outputs
  - backend -> frontend API contract
  - orchestration -> run triggering and delayed feedback lifecycle

### `#72` Track blockers and make decisions on scope if some features need simplification

What this task means:
- identify what can block demo readiness
- cut scope intentionally if needed

Current status:
- `Active / ongoing`

Known blockers:
- route naming mismatch: `POST /simulate` vs `POST /simulations`
- metrics payload incomplete for frontend pages
- `GET /model/state` missing
- preview `POST /decide` behavior missing
- orchestration not fully wired

Possible PM simplifications:
- treat Model page as stretch scope
- treat orchestration-triggered simulation launch as stretch scope
- prioritize working `GET /simulations` + rich `GET /metrics` over advanced model inspection

### `#144` Modeling improvement

What this task means:
- verify whether DS improvements are substantial and usable

Current status:
- `Strong`

Evidence:
- repeatable DS workflow script added
- final output generation added
- modeling docs updated
- final artifacts committed

PM interpretation:
- DS appears ahead of some other teams in reproducibility
- remaining risk is integration into backend/frontend, not lack of DS work

---

## Suggested Testing Order

### Should everything go in this file?

For now: yes, mostly.

This file works well as the PM review and milestone decision log because it combines:
- endpoint reality check
- page dependency check
- PM task matrix
- blocker summary

Later, when the contract is finalized, the cleaner split is:
- `campx/app/backend_requirements.md` -> detailed API contract
- `docs/pm_endpoint_review.md` -> PM review / status / decisions
- `docs/api.md` -> published MkDocs version

### Should you test with `docker compose up --build`?

Yes, but not as the very first and only test.

Recommended order:

1. lightweight code sanity checks
2. backend verification checks that do not require the full stack
3. DB connectivity checks
4. full `docker compose up --build`
5. manual app/API smoke test in browser

### Recommended practical order

#### 1. Python syntax sanity

Good first check:

```bash
python3 -m compileall campx
```

Why:
- fast
- catches obvious syntax/import problems across the repo

#### 2. Backend route/OpenAPI verification

There is a helper script:

```bash
python3 campx/api/verify_openapi.py
```

But caution:
- this script appears to still reference older backend helper names such as `create_customer_record` / `update_customer_record`
- backend now uses `upsert_customer_record`

So this script is useful as a concept, but may currently need updating before you trust its failures.

#### 3. DB connectivity check

There is a useful helper:

```bash
python3 campx/api/check_db_connection.py
```

Use this after the DB is actually running.

It helps verify:
- DB connectivity
- required tables
- a few read helpers

#### 4. Full container build/run

Then run:

```bash
docker compose up --build
```

Why this is important:
- it is the closest thing to real integration
- it checks Dockerfiles, dependencies, service startup order, and runtime wiring

#### 5. Manual smoke test

After containers are up, check:
- Streamlit app loads
- FastAPI docs load at `/docs`
- DB/pgAdmin starts
- API endpoints like `/health` and `/simulations` respond

