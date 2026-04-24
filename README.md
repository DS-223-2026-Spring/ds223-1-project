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
cp campx/.env.example campx/.env   # fill in credentials
docker compose up --build
```

| Service | URL |
|---------|-----|
| Streamlit dashboard | http://localhost:8501 |
| FastAPI docs (Swagger) | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |
| Prefect UI | http://localhost:4200 |

---

## Project Structure

```
ds223-1-project/              ← repo root
├── docker-compose.yml        ← run from here
├── .env
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

## Milestone Task Status

### Orchestration (#11–#15)

| # | Task | Status |
|---|------|--------|
| 11 | Join repo, review architecture | ✅ |
| 12 | Research Prefect, propose usage plan | ✅ Five flows planned in `campx/orchestration/flows.py` |
| 13 | Align with PM/DB/DS on automated steps | ✅ Flow plan references DB schema and DS interaction model |
| 14 | Orchestration plan — manual vs automated jobs | ✅ M2/M3/M4 TODOs documented per flow |
| 15 | Draft orchestration folder/service | ✅ `campx/orchestration/` with Dockerfile |

### PM (#16–#22)

| # | Task | Status |
|---|------|--------|
| 16 | Install MkDocs, initialize docs structure | ✅ `mkdocs.yml` + 7 pages in `docs/` |
| 17 | Design ERD, validate with DB and DS | ✅ Approved schema in `campx/db/1_schema.sql` |
| 18 | Transform repo into service-based structure | ✅ `campx/` with api, app, ds, orchestration |
| 19 | Define contribution rules | ✅ `docs/governance.md` |
| 20 | Track team progress across branches | ✅ Ongoing |
| 21 | Review and merge PRs | ✅ PRs #138, #139, #140 merged |
| 22 | Delete merged branches | ⚠️ Remote branches `db`, `ds`, `backend`, `front` still exist |

### DB (#23–#31)

| # | Task | Status |
|---|------|--------|
| 23 | Create `db` branch | ✅ |
| 24 | Create `db` database container | ✅ `db` service in `docker-compose.yml` |
| 25 | Set up PostgreSQL from ERD | ✅ `campx/db/1_schema.sql` |
| 26 | Tables, keys, relationships, constraints | ✅ 8 tables with FK constraints and CHECK rules |
| 27 | Python code to connect and verify | ✅ `campx/db/SQLHandler.py` |
| 28 | Load flat-file data, validate row counts | ✅ `campx/db/3_initial_insert.sql` + `db_interactions.py` |
| 29 | Reusable insert/update/select/delete helpers | ✅ `campx/db/db_interactions.py` |
| 30 | Document utilities with docstrings | ✅ |
| 31 | Push to `db` branch, open PR | ✅ Merged via PR #138 |

### DS (#32–#40)

| # | Task | Status |
|---|------|--------|
| 32 | Create `ds` branch | ✅ |
| 33 | Create `ds` container | ✅ `ds` service in `docker-compose.yml` |
| 34 | Explore data, identify quality issues | ✅ `campx/ds/eda.py` |
| 35 | Simulate/generate data, document synthetic sources | ✅ `campx/ds/synthetic/` — fully documented |
| 36 | Use DB CRUD wherever possible | ✅ Uses `campx/etl/db_interactions.py` |
| 37 | EDA notebook/script | ✅ `campx/ds/eda.py` + `campx/ds/experiments.ipynb` |
| 38 | Baseline models and comparison | ✅ `campx/ds/baselines.py` |
| 39 | Document features, assumptions, target variable | ✅ `docs/ds_data_spec.md` |
| 40 | Push to `ds` branch, open PR | ✅ Merged |

### Backend (#41–#49)

| # | Task | Status |
|---|------|--------|
| 41 | Create `back` branch | ⚠️ Branch named `backend` not `back` |
| 42 | Create backend container | ✅ `api` service in `docker-compose.yml` |
| 43 | Coordinate with PM/DB on API structure | ✅ Documented in `campx/app/backend_requirements.md` |
| 44 | FastAPI with clean folder structure | ✅ `campx/api/` with `routes/` |
| 45 | Dummy CRUD endpoints (GET, POST, PUT, DELETE) | ✅ customers, bandit, simulations routes |
| 46 | Placeholder request/response schemas | ⚠️ `campx/api/schema.py` exists but empty |
| 47 | Test endpoints, verify Swagger at `/docs` | ✅ Swagger auto-generated and accessible |
| 48 | Document API assumptions | ✅ `docs/api.md` + `campx/app/backend_requirements.md` |
| 49 | Push to branch, open PR | ✅ Merged |

### Frontend (#50–#57)

| # | Task | Status |
|---|------|--------|
| 50 | Create `front` branch | ✅ |
| 51 | Create frontend container | ✅ `front` service in `docker-compose.yml` |
| 52 | Coordinate with PM on Streamlit page structure | ✅ `campx/app/backend_requirements.md` |
| 53 | Build UI skeleton with navigation and layout | ✅ 4 pages in `campx/app/pages/` |
| 54 | Reusable UI components/helpers | ✅ `campx/app/bandit_utils.py` |
| 55 | Placeholders for charts, forms, model output | ✅ All 4 pages wired with mock data |
| 56 | Document data needs from backend | ✅ `campx/app/backend_requirements.md` — comprehensive endpoint spec |
| 57 | Push to `front` branch, open PR | ✅ Merged via PRs #139, #140 |

---

## Milestones

| Milestone | Due | Focus |
|-----------|-----|-------|
| M1 | Apr 12 | Problem definition, roles, roadmap, prototype |
| M2 | Apr 21 | DB schema, customer generation, LinUCB |
| M3 | May 1 | API, Streamlit, Prefect integration |
| M4 | May 8 | Testing, documentation, polish |
| Demo | May 14 | Live demonstration |
