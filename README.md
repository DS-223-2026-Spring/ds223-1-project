# CampX — Campaign Optimization Engine

**DS 223 · Marketing Analytics · Group 1 · Spring 2026 · AUA**

A contextual bandit system (LinUCB) that selects the optimal promotional action for each fashion retail customer — learning which offer maximises net profit for which customer profile, updating after every interaction.

---

## Team

| Role | Member | Branch |
|------|--------|--------|
| PM | Anna Asatryan | `main` |
| DB Developer | Hayk Alekyan | `db` |
| Backend | Victoria Makaryan | `backend` |
| Frontend | Armine Babajanyan | `front` |
| Data Scientist | Davit Badalyan | `ds` |
| Orchestration | *(shared)* | `orchestration` |

---

## Quick Start

```bash
git clone https://github.com/DS-223-2026-Spring/ds223-1-project
cd ds223-1-project
docker compose up --build
```

| Service | URL |
|---------|-----|
| Streamlit dashboard | http://localhost:8501 |
| FastAPI docs (Swagger) | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |

---

## Project Structure

```
ds223-1-project/              ← repo root
├── docker-compose.yml        ← run from here
├── README.md
├── mkdocs.yml
├── docs/                     ← MkDocs documentation
│   ├── index.md
│   ├── governance.md
│   ├── database.md
│   ├── modeling.md
│   ├── ds_data_spec.md
│   ├── api.md
│   └── frontend.md
└── campx/                    ← product folder
    ├── .env                  ← all service credentials
    ├── __init__.py
    ├── api/                  ← FastAPI backend (Victoria)
    │   ├── Dockerfile
    │   ├── main.py
    │   ├── database.py
    │   ├── models.py
    │   ├── schema.py
    │   ├── requirements.txt
    │   └── routes/
    │       ├── customers.py
    │       ├── bandit.py
    │       └── simulations.py
    ├── app/                  ← Streamlit frontend (Armine)
    │   ├── Dockerfile
    │   ├── app.py
    │   ├── bandit_utils.py
    │   ├── requirements.txt
    │   └── pages/
    │       ├── 1_create_simulation.py
    │       ├── 2_interaction.py
    │       ├── 3_analytics.py
    │       └── 4_model.py
    ├── ds/                   ← Data Science (Davit)
    │   ├── Dockerfile
    │   ├── main.py
    │   ├── etl.py
    │   ├── eda.py
    │   ├── baselines.py
    │   ├── model.py
    │   ├── experiments.ipynb
    │   ├── generate_eda_report.py
    │   ├── generate_final_outputs.py
    │   ├── generate_synthetic_data.py
    │   ├── run_baseline_comparison.py
    │   ├── run_workflow.py
    │   ├── requirements.txt
    │   └── synthetic/        ← synthetic data generation module
    ├── db/                   ← DB schema & helpers (Hayk)
    │   ├── 1_schema.sql
    │   ├── 2_indexes.sql
    │   ├── 3_initial_insert.sql
    │   ├── SQLHandler.py
    │   └── db_interactions.py
    ├── etl/                  ← shared ETL utilities
    │   ├── SQLHandler.py
    │   └── db_interactions.py
    └── orchestration/        ← Prefect flows (shared)
        ├── Dockerfile
        ├── flows.py
        └── requirements.txt
```

All Dockerfiles use `python:3.13-slim`.

---

## Branching & Commits

```
main  ← protected, PM merges here
├── db
├── backend
├── ds
├── front
└── orchestration
```

Commit format: `role: short description`
Examples: `db: add crud helpers` · `ds: implement linucb` · `backend: add /decide endpoint`

Full contribution rules: [`docs/governance.md`](docs/governance.md)


---

## Milestones

| Milestone | Due | Focus |
|-----------|-----|-------|
| M1 | Apr 12 | Problem definition, roles, roadmap, prototype |
| M2 | Apr 21 | DB schema, customer generation, LinUCB |
| M3 | May 1 | API, Streamlit, Prefect integration |
| M4 | May 8 | Testing, documentation, polish |
| Demo | May 14 | Live demonstration |
