# DS223 Group Project

## Product

CampX is a contextual bandit system for marketing decision-making in fashion retail.
The product chooses one of five promotional actions for each customer and updates
its decision logic from observed outcomes.

## Stack

| Layer | Technology |
|------|------------|
| Database | PostgreSQL |
| Frontend | Streamlit |
| Backend | FastAPI |
| Documentation | MkDocs |

## Problem

Sending the same promotion to every customer wastes budget and hurts margin.
Different customer profiles respond to different actions, so the system needs to
learn which action is best for each context.

## Solution

The project uses LinUCB to choose among five actions:

- no action
- 10% discount
- free shipping
- product recommendation
- bundle offer

The model observes customer RFM-style features and updates after interactions.

## Quick start

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Streamlit dashboard | `http://localhost:8501` |
| FastAPI docs | `http://localhost:8000/docs` |
| pgAdmin | `http://localhost:5050` |

## Team

| Role | Branch |
|------|--------|
| PM | `pm` |
| Database | `db` |
| Backend | `backend` |
| Frontend | `frontend` |
| Data Science | `ds` |
| Orchestration | `orch` |
