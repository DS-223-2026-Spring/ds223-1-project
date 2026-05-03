# Project Governance

## 1. Team Roles & Responsibilities

| Role | Member | Branch | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **PM** | Anna | `pm` | Repo structure, MkDocs, PR reviews, milestone tracking (#16–22, #68–72) |
| **DB Developer** | Hayk | `db` | PostgreSQL schema, CRUD helpers, seed data (#23–31, #73–77) |
| **Backend** | Victoria | `backend` | FastAPI routes, SQLAlchemy models, Pydantic schemas (#41–49) |
| **Frontend** | Armine | `frontend` | Streamlit pages, dashboard charts, simulation controls (#50–57) |
| **Data Scientist** | Davit | `ds` | Customer generation, LinUCB, simulation loop, baselines (#32–40, #78–81) |
| **Orchestration** | *(shared)* | `orchestration` | Prefect flows, scheduling, outcome loop (#11–15, #58–67) |

---

## 2. Dependency Order — who does what first

```
[1] Anna (pm)
Finalises repo structure, schema, docs, pushes to master
↓
[2] Hayk (db)
Implements db/init.sql, db/crud.py helpers
Verifies PostgreSQL + seed data running
↓
[3] Davit (ds)
Uses Hayk's CRUD to write generated customers to DB
Implements LinUCB — reads customers, writes interactions + model_state
↓
[4] Victoria (backend)          [4] Armine (frontend)
Implements /decide               Builds dashboard pages
Implements /feedback             Connects to /metrics endpoint
Implements /metrics
↓
[5] Orchestration (shared)
Prefect flows wire everything into a continuous loop
```

Victoria and Armine can set up skeletons in parallel from step 1.
Their real implementation depends on Hayk finishing CRUD first.

---

## 3. Branching Strategy

```
master  (protected — PM merges here only)
├── pm           Anna: mkdocs, structure, governance
├── db           Hayk: schema, CRUD
├── backend      Victoria: FastAPI
├── frontend     Armine: Streamlit
├── ds           Davit: customer gen, LinUCB
└── orchestration  Prefect flows
```

One branch per person. Push directly to your branch.
Open one PR to master when your M2 work is complete.

---

## 4. Contribution Standards

### Commit message format

```
<role>: <short description>
```

db: implement get_customer_latents helper
ds: add LinUCB select_action and update methods
backend: add /decide endpoint with DB connection
frontend: cumulative reward chart on dashboard page
pm: fix governance dependency order
orchestration: implement decision_loop flow

### Pull Request process

1. Push your branch: `git push origin <branch>`
2. Open PR targeting **master**
3. Write 2–3 sentences: what changed and why
4. Tag **Anna** as reviewer — do not merge your own PR
5. Anna reviews, merges, and deletes the branch
