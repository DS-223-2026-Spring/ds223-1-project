# CampX Documentation

CampX is a marketing analytics MVP for promotional campaign optimization. It connects a Streamlit frontend, FastAPI backend, PostgreSQL database, and Python data science pipeline into a runnable end-to-end system.

The project uses synthetic retail-style customer data to demonstrate how customer context can support promotional action selection and campaign performance analysis.

## Project Scope

CampX focuses on promotional action-type selection. Given RFM-style customer features, the system evaluates five action types:

- no action
- 10% discount
- free shipping
- product recommendation
- bundle offer

Reward is defined as simulated realized revenue minus promotional action cost.

The project is an MVP for DS223 Marketing Analytics. It demonstrates architecture, integration, and decision-support logic. It is not a production marketing platform.

## Architecture Summary

```text
Data Science pipeline → PostgreSQL → FastAPI → Streamlit dashboard
```

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Streamlit | Dashboard and user-facing workflow |
| Backend | FastAPI | API endpoints and application logic |
| Database | PostgreSQL | Structured storage for customers, simulations, interactions, and model state |
| Data Science | Python | Synthetic data, contextual bandit logic, baselines, and artifacts |
| Documentation | MkDocs | Project reference and demo overview |

## Documentation Sections

- **Demo** — presentation-facing project overview and live demo flow.
- **Integration** — service responsibilities and cross-service contracts.
- **API** — backend endpoints and dashboard-facing responses.
- **Database** — schema, tables, views, and procedures.
- **Modeling** — synthetic data, LinUCB logic, baselines, and limitations.
- **App** — Streamlit page structure and frontend behavior.
- **Docker** — local run instructions.

## Quick Start

From the repository root:

```bash
docker compose up --build
```

## Useful URLs

| Service | URL |
|---|---|
| Streamlit frontend | <http://localhost:8501> |
| FastAPI Swagger docs | <http://localhost:8000/docs> |
| pgAdmin | <http://localhost:5050> |
| Mkdocs documentation | <https://ds-223-2026-spring.github.io/ds223-1-project/> |


## Scope Notes

- Synthetic data only.
- Promotional action-type selection only.
- No real customer data.
- No production deployment.
- No item-level SKU recommendation in the current MVP.
- Dedicated workflow scheduling is out of final MVP scope; the project uses the DS batch workflow and API/database integration path.