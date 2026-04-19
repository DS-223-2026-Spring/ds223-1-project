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

---

## 5. Change from M1 proposal

M1 proposed a hybrid approach using UCI Online Retail II for customer features.
After evaluation the dataset was found to be a UK giftware wholesaler with 25%
missing customer IDs — incompatible with the fashion retail domain and insufficient
for grounding the simulation meaningfully.

The revised approach is fully simulated using a latent generative model. This
was also motivated by a methodological concern: simulating conversion directly
from RFM features makes the learning problem trivially easy. Latent traits introduce
genuine noise between observable context and reward signal, making the bandit
problem non-trivial and the results more academically defensible.

Note: M1 listed latent traits as out of scope. This decision reverses that.
The rationale is documented above.

---

## 6. Definition of Done — M2 (Due April 21)

### PM — Anna
- [x] Repository structure finalised
- [x] `docker-compose.yml` correct with all services
- [x] MkDocs live — all pages render
- [x] Governance and ERD published
- [ ] All M2 PRs reviewed and merged
- [ ] Merged branches deleted

### DB — Hayk
- [ ] `docker-compose up db` starts PostgreSQL 17 cleanly
- [x] `db/init.sql` schema complete and validated
- [ ] `db/init.sql` runs without error on fresh container
- [ ] All 6 tables visible in pgAdmin: `customers`, `customer_latents`, `actions`, `simulations`, `interactions`, `model_state`
- [ ] `actions` table has 5 seeded rows with correct £ cost values
- [ ] `db/crud.py` — all helpers implemented with docstrings
- [ ] `python db/crud.py` smoke test passes
- [ ] PR open: `db` → `master`

### Data Science — Davit
- [ ] `docker-compose up ds` runs without error
- [ ] 500 customers generated and visible in `customers` table
- [ ] `customer_latents` populated with same 500 rows
- [ ] LinUCB runs 1000 rounds, `interactions` table populated
- [ ] `model_state` has 5 rows (one per action) after simulation
- [ ] Random and heuristic baselines implemented
- [ ] PR open: `ds` → `master`

### Backend — Victoria
- [ ] `docker-compose up api` starts cleanly
- [ ] Swagger accessible at `http://localhost:8000/docs`
- [ ] All routes return placeholder responses
- [ ] PR open: `backend` → `master`

### Frontend — Armine
- [ ] `docker-compose up app` starts cleanly
- [ ] All 4 pages load in Streamlit sidebar without errors
- [ ] PR open: `frontend` → `master`

### Orchestration
- [ ] `docker-compose up prefect` starts Prefect UI at port 4200
- [ ] `flows.py` imports without error
- [ ] Short proposal written: which flows automate in M3
- [ ] PR open: `orchestration` → `master`