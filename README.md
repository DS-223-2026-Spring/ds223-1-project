# CampX — Marketing Campaign Optimization MVP

**DS 223 · Marketing Analytics · Group 1 · Spring 2026 · AUA**

CampX is a marketing analytics MVP for campaign optimization. It demonstrates how a marketing team could use customer context to choose among promotional action types, track simulated outcomes, and inspect campaign performance through an end-to-end microservice architecture.

The project connects a Streamlit frontend, FastAPI backend, PostgreSQL database, and Python data science workflow using Docker Compose. The data is synthetic retail-style customer data, designed for a course MVP rather than production deployment.

---

## Problem

Marketing teams often send the same discount or offer to broad customer groups. This can waste budget because different customers respond differently to promotions, and some customers may not need an incentive at all.

CampX addresses this as a decision-support problem: given customer behavioral features, choose a promotional action that balances expected value and promotional cost.

---

## Solution

CampX models campaign decisions as a contextual bandit problem using LinUCB-style logic. For each customer interaction, the system uses RFM-style customer features to select one of five promotional action types:

- No action
- 10% discount
- Free shipping
- Product recommendation
- Bundle offer

Reward is defined as:

```text
simulated realized revenue - promotional action cost
```

The system tracks cumulative net campaign value, compares the selected policy against a random baseline, and exposes action-level performance, customer-level features, and model state through the dashboard.

The recommended action is the highest-scoring action under the current model. It should not be interpreted as a guaranteed optimal business decision.

---

## Architecture

| Layer | Service | Path | Purpose |
|---|---|---|---|
| Frontend | Streamlit | `campx/app` | User-facing campaign dashboard |
| Backend | FastAPI | `campx/api` | API contract and application logic |
| Database | PostgreSQL | `campx/db` | Tables, views, procedures, seed data, simulation storage |
| Data Science | Python DS workflow | `campx/ds` | Synthetic data, LinUCB campaign simulation, baselines, artifacts |
| Documentation | MkDocs | `docs/` | Project documentation and demo guide |

Docker Compose runs the services locally and connects the frontend, backend, database, and data science workflow.

---

## Repository Structure

## Repository Structure

```text
ds223-1-project/
├── .github/                  # GitHub workflow and PR template
│   └── workflows/
│       └── ci.yaml           # CI workflow for project checks / docs build
├── campx/                    # Product source code
│   ├── .env                  # Local development environment defaults
│   ├── __init__.py
│   ├── api/                  # FastAPI backend, schemas, routes, DB helpers
│   ├── app/                  # Streamlit frontend, assets, pages, API client helpers
│   ├── db/                   # PostgreSQL schema, indexes, seed data, views, procedures
│   └── ds/                   # Synthetic data, LinUCB workflow, baselines, final outputs
├── docs/                     # Source documentation for MkDocs
├── outputs/final_outputs/    # Generated DS outputs used for reproducibility/reference
├── docker-compose.yml        # Local multi-service runtime
├── mkdocs.yaml               # MkDocs configuration
├── README.md                 # Repository entry point
├── LICENSE
└── .gitignore
```

---

## Data Flow

1. The DS workflow generates synthetic customers, LinUCB campaign interactions, model state, baselines, and artifacts.
2. DS outputs are persisted to PostgreSQL.
3. FastAPI reads from and writes to PostgreSQL through API endpoints.
4. Streamlit calls the FastAPI backend and visualizes campaign setup, live decisions, performance, decision logic, and customer profiles.

---

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/DS-223-2026-Spring/ds223-1-project.git
cd ds223-1-project
```

### 2. Check environment defaults

The project expects a local environment file at:

```text
campx/.env
```

For the course demo, this file contains development defaults for PostgreSQL, pgAdmin, and service configuration. No changes are needed for a standard local run.

Do not commit real production credentials or private secrets.

### 3. Build and start the stack

```bash
docker compose down -v
docker compose up --build
```

This starts:

| Service | URL |
|---|---|
| Streamlit frontend | <http://localhost:8501> |
| FastAPI Swagger docs | <http://localhost:8000/docs> |
| pgAdmin | <http://localhost:5050> |
| MkDocs documentation | <https://ds-223-2026-spring.github.io/ds223-1-project/> |

The DS container runs as a batch job. It generates and persists synthetic customers, LinUCB campaign interactions, model state, baselines, and artifacts, then exits with code `0`. This is expected.

---

## Verify the Stack

After startup, run:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/actions
curl "http://localhost:8000/customers?limit=2"
curl http://localhost:8000/simulations
curl "http://localhost:8000/metrics?simulation_id=1"
curl "http://localhost:8000/model/state?simulation_id=1"
```

A working demo run should include customers, five promotional actions, at least one completed campaign run, and non-empty metrics/model state.

---

## Documentation

Full project documentation is available at:

<https://ds-223-2026-spring.github.io/ds223-1-project/>

The documentation includes the demo guide, API overview, database notes, data science/modeling page, frontend page, Docker notes, and integration map.

---

## Demo Notes

The default local demo uses a synthetic LinUCB campaign run with 500 customers and 5,000 interaction rounds.

For the safest demo, use the existing completed campaign run rather than launching a new long run live. Incremental one-step simulation is supported through the backend, but the main demo path relies on the completed run for stability.

---

## Scope and Limitations

- Synthetic retail-style data only
- No real customer profiles or production campaign deployment
- Simplified five-action promotional action space
- Simplified one-step reward model
- No item-level SKU or bundle recommendation in the current model
- No production monitoring, authentication, or budget-governance layer
- Dedicated workflow scheduling was removed from final MVP scope; the runnable path is DS batch workflow → PostgreSQL → FastAPI → Streamlit

---

## Team

| Role | Member | Branch |
|---|---|---|
| PM | Anna Asatryan | `main` |
| DB Developer | Hayk Alekyan | `db` |
| Backend | Victoria Makaryan | `backend` |
| Frontend | Armine Babajanyan | `front` |
| Data Scientist | Davit Badalyan | `ds` |
