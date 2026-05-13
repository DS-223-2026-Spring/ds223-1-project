# Integration Map

## Service Responsibilities

| Service | Technology | Role |
|---------|------------|------|
| Frontend | Streamlit | Dashboard for campaign setup, live decisions, performance analytics, decision logic, and customer explorer |
| Backend | FastAPI | REST API exposing customers, actions, campaign runs, metrics, model state, decisions, feedback, and baselines |
| Database | PostgreSQL | Tables, views, stored procedures, seed data, interaction records, campaign artifacts, and model state persistence |
| Data Science | Python pipeline | Synthetic customer generation, contextual bandit simulation, baseline comparison, artifact persistence |
| Documentation | MkDocs | Project docs site |

---

## PM Integration Review

The PM role coordinated the endpoint list, frontend/backend contract, and final service alignment. The final MVP scope was reviewed across four active services:

- Streamlit frontend pages consume FastAPI endpoints through `bandit_utils.py`.
- FastAPI exposes customers, actions, simulations, metrics, model state, decisions, feedback, and baselines.
- PostgreSQL stores customers, actions, simulations, interactions, model state, and DS artifacts.
- The DS workflow persists synthetic customers, LinUCB campaign interactions, model state, baselines, and final artifacts to PostgreSQL.

Earlier orchestration-specific planning was removed from final MVP scope. The final runnable path is shown below:

---

## End-to-End Data Flow

```
DS pipeline
  │
  │ 1. Generates synthetic customers, campaign interactions,
  │    model state, and artifacts (baselines, summaries)
  │
  ▼
PostgreSQL
  │
  │ 2. DS persists all outputs via POST /ds/artifacts
  │    (customers, interactions, model_state, baselines CSV)
  │
  ▼
FastAPI
  │
  │ 3. Reads/writes PostgreSQL; exposes all endpoints
  │    at http://localhost:8000
  │
  ▼
Streamlit
    4. Calls FastAPI endpoints and renders
       dashboard pages at http://localhost:8501
```

---


## API Contracts Used by Frontend

| Frontend need | Endpoint | Purpose |
|---------------|----------|---------|
| Service health | `GET /health` | Confirm backend is running |
| Action catalog | `GET /actions` | List the 5 promotional action types |
| Customer list | `GET /customers` | RFM profiles for the Customer Explorer |
| Customer detail | `GET /customers/{customer_id}` | Profile, RFM, and interaction history |
| Campaign run list | `GET /simulations` | Populate the sidebar campaign run selector |
| New campaign run | `POST /simulations` | Launch a new campaign run from Campaign Setup |
| Incremental step | `POST /simulations/{simulation_id}/step` | Run one LinUCB round (live demo path) |
| Dashboard metrics | `GET /metrics` | All Performance and Live Decisions chart data |
| Model weights | `GET /model/state` | Theta matrix and pull counts for Decision Logic |
| Action preview | `POST /decide?preview=true` | UCB score breakdown for one customer |
| Outcome feedback | `POST /feedback` | Record interaction result and update model |
| Baseline curve | `GET /baselines` | Random policy reward series for Performance chart |

---

## Demo Contract

The following known-good state is pre-loaded for the demo:

| Item | Value |
|------|-------|
| `simulation_id` | 1 (completed) |
| Customers | 500 |
| Interaction rounds | 5,000 |
| Actions | 5 promotional action types |
| Reward formula | `revenue − action_cost` |
| Policy | LinUCB contextual bandit |
| Baseline | Random uniform over the same 5 actions |

---

## Out of Scope

| Item | Status |
|------|--------|
| Production deployment | Not included — MVP only |
| Real customer data | Not used — all data is synthetic |
| Item-level SKU recommendation | Not included — action-type selection only |
| Real-time streaming | Not implemented — incremental API step used instead |
