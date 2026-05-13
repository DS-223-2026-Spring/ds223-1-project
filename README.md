# CampX — Marketing Campaign Optimization MVP

**DS 223 · Marketing Analytics · Group 1 · Spring 2026 · AUA**

CampX is a marketing analytics MVP for campaign optimization. It demonstrates how a marketing team could use customer context to choose among promotional action types, track simulated outcomes, and inspect campaign performance through an end-to-end microservice architecture.

The project connects a Streamlit frontend, FastAPI backend, PostgreSQL database, and Python data science pipeline using Docker Compose. The data is synthetic retail-style customer data, designed for a course MVP rather than production deployment.

## Problem

Marketing teams often send the same discount or offer to broad customer groups. This can waste budget because different customers respond differently to promotions, and some customers may not need an incentive at all.

CampX addresses this as a decision-support problem: given customer behavioral features, choose a promotional action that balances expected value and promotional cost.

## Solution

CampX models campaign decisions as a contextual bandit problem using LinUCB-style logic. For each customer interaction, the system uses RFM-style customer features to select one of five promotional action types:

- no action
- 10% discount
- free shipping
- product recommendation
- bundle offer

Reward is defined as:

```text
simulated realized revenue - promotional action cost
```

The system tracks cumulative net campaign value, compares the selected policy against a random baseline, and exposes action-level performance, customer-level features, and model state through the dashboard.

The recommended action is the highest-scoring action under the current model. It should not be interpreted as a guaranteed optimal business decision.

## Architecture

| Layer | Service | Path | Purpose |
|---|---|---|---|
| Frontend | Streamlit | `campx/app` | User-facing campaign dashboard |
| Backend | FastAPI | `campx/api` | API contract and application logic |
| Database | PostgreSQL | `campx/db` | Tables, views, procedures, seed data, simulation storage |
| Data Science | Python DS pipeline | `campx/ds` | Synthetic data, contextual bandit logic, baselines, artifacts |
| Documentation | MkDocs | `docs/` | Project documentation and demo guide |

Docker Compose runs the services locally and connects the frontend, backend, database, and data science workflow.

## Repository Structure

```text
ds223-1-project/
├── docker-compose.yml        # Local multi-service runtime
├── README.md                 # Repository entry point
├── mkdocs.yaml               # MkDocs configuration
├── LICENSE
├── docs/                     # Source documentation for MkDocs
└── campx/                    # Product source code
    ├── api/                  # FastAPI backend
    ├── app/                  # Streamlit frontend
    ├── db/                   # PostgreSQL schema, views, procedures, seed data
    ├── ds/                   # Synthetic data, LinUCB, baselines, final outputs
    └── etl/                  # ETL-related project folder
```

## Data Flow

1. The DS pipeline generates synthetic customers, campaign interactions, model state, and artifacts.
2. DS outputs are persisted to PostgreSQL.
3. FastAPI reads from and writes to PostgreSQL through API endpoints.
4. Streamlit calls the FastAPI backend and visualizes campaign setup, live decisions, performance, decision logic, and customer profiles.

## Quickstart

Build and run the local stack:

```bash
docker compose up --build
```

Service URLs:

| Service | URL |
|---|---|
| Streamlit frontend | <http://localhost:8501> |
| FastAPI Swagger docs | <http://localhost:8000/docs> |
| pgAdmin | <http://localhost:5050> |
| Mkdocs documentation | <https://ds-223-2026-spring.github.io/ds223-1-project/> |

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

A working demo run should include customers, five promotional actions, at least one completed campaign run, and non-empty metrics.

## Documentation

Full project documentation is available at:

<https://ds-223-2026-spring.github.io/ds223-1-project/>

The documentation includes the demo guide, API overview, database notes, data science pipeline, frontend pages, and integration map.

## Demo Notes

The default local demo uses a synthetic campaign run with 500 customers and 5000 interaction rounds. The DS container runs as a batch job: it generates or persists data and then exits successfully. This is expected behavior.

For the safest demo, use the existing completed campaign run rather than launching a new long run live.


## Scope and Limitations

- Synthetic retail-style data only
- No real customer profiles or production campaign deployment
- Simplified five-action promotional action space
- Simplified one-step reward model
- No item-level SKU or bundle recommendation in the current model
- No production monitoring or alerting
- Dedicated workflow scheduling was removed from final MVP scope; the runnable path is DS batch workflow → PostgreSQL → FastAPI → Streamlit

## Team

| Role | Member | Branch |
|---|---|---|
| PM | Anna Asatryan | `main` |
| DB Developer | Hayk Alekyan | `db` |
| Backend | Victoria Makaryan | `backend` |
| Frontend | Armine Babajanyan | `front` |
| Data Scientist | Davit Badalyan | `ds` |
