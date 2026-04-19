# CampX — Campaign Optimization Engine

**DS 223 · Marketing Analytics · Group 1 · Spring 2026 · AUA**

A contextual bandit system (LinUCB) that selects the optimal promotional
action for each fashion retail customer — learning which offer maximises
net profit for which customer profile, updating after every interaction.

---

## Team

| Role | Member | Branch |
|------|--------|--------|
| PM | Anna Asatryan | `pm` |
| DB Developer | Hayk Alekyan | `db` |
| Backend | Victoria Makaryan | `backend` |
| Frontend | Armine Babajanyan | `frontend` |
| Data Scientist | Davit Badalyan | `ds` |
| Orchestration | *(shared)* | `orchestration` |

---

## Quick start

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Streamlit dashboard | http://localhost:8502 |
| FastAPI docs | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 — admin@admin.com / admin123 |
| Prefect UI | http://localhost:4200 |

---

## Project structure

```
ds223-1-project/
├── backend/              FastAPI backend (Victoria)
│   ├── Dockerfile
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schema.py
│   └── requirements.txt
├── frontend/             Streamlit frontend (Armine)
│   ├── Dockerfile
│   ├── app.py
│   ├── pages/
│   │   ├── page1.py
│   │   ├── page2.py
│   │   ├── page3.py
│   │   └── page4.py
│   └── requirements.txt
├── db/                   Database (Hayk)
│   ├── init.sql
│   └── crud.py
├── ds/                   Data Science (Davit)
│   ├── Dockerfile
│   ├── main.py
│   ├── etl.py
│   └── model.py
├── orchestration/        Prefect flows (shared)
│   ├── Dockerfile
│   ├── flows.py
│   └── requirements.txt
├── docs/                 MkDocs documentation (Anna)
├── milestone1/           M1 deliverables
├── docker-compose.yml
├── mkdocs.yml
├── .env                  Local config — never committed
└── .gitignore
```

---

## Branching

One branch per role. Push directly to your branch, open one PR to main when ready.
main  (protected — Anna merges here)
├── pm
├── db
├── backend
├── frontend
├── ds
└── orchestration

Commit format: `db: add crud helpers` / `ds: implement linucb` / `backend: add /decide endpoint`

Full contribution rules: `docs/governance.md`

---

## Milestones

| Milestone | Due | Focus |
|-----------|-----|-------|
| M1 | Apr 12 | Problem definition, roles, roadmap, prototype |
| M2 | Apr 21 | DB schema, customer generation, LinUCB |
| M3 | May 1 | API, Streamlit, Prefect integration |
| M4 | May 8 | Testing, documentation, polish |
| Demo | May 14 | Live demonstration |