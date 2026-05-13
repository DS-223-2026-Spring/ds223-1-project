# Backend API — FastAPI

## Overview

The CampX backend is a FastAPI service that connects the Streamlit frontend to PostgreSQL-backed campaign data, model state, customer profiles, and baseline outputs. It also exposes supporting endpoints for simulation lifecycle and DS artifact access.

Base URL (local):

```
http://localhost:8000
```

Swagger UI (interactive docs):

```
http://localhost:8000/docs
```

## Endpoint Reference

| Endpoint | Method | Purpose | Used by |
|----------|--------|---------|---------|
| `/` | GET | API root — service name, status, links | Browser / health check |
| `/health` | GET | Confirm the service is running | All pages, monitoring |
| `/actions` | GET | List the 5 promotional action types | Campaign Setup |
| `/customers` | GET | List customers with RFM features | Customer Explorer |
| `/customers/{customer_id}` | GET | Fetch one customer with interaction history | Customer detail view |
| `/simulations` | GET | List all campaign run records | All pages (sidebar) |
| `/simulations` | POST | Create and launch a new campaign run | Campaign Setup |
| `/simulations/{simulation_id}` | GET | Fetch one campaign run record | Internal |
| `/simulations/{simulation_id}/step` | POST | Run one LinUCB round (incremental demo path) | Live Decisions |
| `/simulations/{simulation_id}/complete` | PUT | Mark a campaign run as completed | Internal |
| `/metrics` | GET | Read aggregated metrics for a campaign run | Performance, Live Decisions |
| `/model/state` | GET | Inspect LinUCB theta weights and pull counts | Decision Logic |
| `/decide` | POST | Score actions for a customer; optionally log | Decision Logic |
| `/feedback` | POST | Record outcome and update model weights | Internal / DS pipeline |
| `/baselines` | GET | Return random policy baseline reward array | Performance |
| `/ds/artifacts` | POST | Import DS-generated data bundle | DS pipeline |
| `/ds/artifacts/{simulation_id}` | GET | List DS artifact names | Internal |
| `/ds/artifacts/{simulation_id}/{artifact_name}` | GET | Fetch one DS artifact | Internal |
| `/assumptions` | GET | API contract assumptions | Internal |

## Key Endpoint Notes

- **`/metrics`** returns `cumulative_reward_series`, `action_distribution`, `conversion_by_action`, and `segment_performance`. All Performance page charts and KPIs come from this single endpoint call.
- **`/model/state`** exposes theta weight matrix and per-action pull counts used by the Decision Logic page.
- **`/baselines`** reads the pre-generated `policy_round_traces.csv` artifact from the DS pipeline and returns the random-uniform baseline reward series.
- **`/simulations/{simulation_id}/step`** supports incremental one-round simulation. It is available for live-update demos, while the safest final demo uses an already completed campaign run.
- **`/decide?preview=true`** returns the UCB decomposition (exploit + explore + ucb_score) without logging an interaction. This is what the Decision Logic page uses for single-customer previews.
- **`/customers/{id}?debug=true`** includes simulation-only hidden variables (latent traits used by the simulator). These are excluded from the normal response to preserve the LinUCB assumption that only RFM features are observable.

## Backend Reference

### `main.py`

::: campx.api.main

### `schemas.py`

::: campx.api.schemas

### `crud.py`

::: campx.api.crud