# Project Governance

## 1. Team Roles & Responsibilities

The following roles are assigned to ensure the "Adaptive Campaign Optimization Engine" meets all Milestone requirements.

| Role | Member | Primary Branch | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **PM / Lead** | Anna | `pm` | Repo architecture, MkDocs, PR reviews, milestone tracking (#16–22). |
| **DB Developer** | Hayk | `db` | PostgreSQL schema, CRUD helpers, data loading (#23–31). |
| **Backend** | Victoria | `backend` | FastAPI routes, logic, integration, API docs (#41–49). |
| **Frontend** | Armine | `frontend` | Streamlit pages, dashboards, API consumption (#50–57). |
| **Data Scientist** | Davit | `ds` | EDA, simulation engine, LinUCB model logic (#32–40). |
| **Orchestration** | *(Shared)* | `orchestration` | Prefect flows and service automation (#11–15, #58–67). |

---

## 2. Branching Strategy

We follow a hierarchical branching model to protect the stability of the project.

- **`master` (Protected)**: Only contains reviewed and approved work. No direct pushes allowed.
- **Role Branches**: Long-lived branches (`db`, `ds`, `backend`, `frontend`, `pm`) where major service components are integrated.
- **Feature Branches**: Temporary branches created for specific tasks (e.g., `db/add-indexes`, `ds/linucb-init`).

### Workflow

feature-branch → role-branch → master

---

## 3. Contribution Standards

### Commit message format

Use role-based prefixes to keep the history readable:

db: implement customer table schema
ds: add LinUCB update logic
backend: add /predict endpoint
frontend: add simulation results chart
pm: update mkdocs navigation
orchestration: draft Prefect flow plan

### Pull Request process

1. **Push your branch**: `git push origin <feature-branch>`
2. **Open a PR**: Target your **role branch** (e.g., `ds/eda-notebook` → `ds`, not `master`)
3. **Notify for review**: Tag Anna as the reviewer
4. **No self-merging**: The PM reviews and merges into role branches, then finally into `master`
5. **Cleanup**: Delete the feature branch immediately after it is merged

---

## 4. Communication & Sync

- **Slack**: All blockers must be posted in `#group-1` by **10:00 AM daily**
- **Project Board**: Anna tracks all tasks (#2–#71) via the GitHub Projects board
- **Deadlines**: All M2 code must be in an open PR by **April 20** to meet the **April 21** deadline

---

## 5. Milestone 2: Definition of Done (Due April 21)

All of the following must be complete and merged (or in a reviewed PR) by April 21.

### Project Management (`pm`) — Anna

- [ ] `pm` branch exists and is up to date (#19, #20)
- [ ] MkDocs initialised, all pages render without errors (#16)
- [ ] Governance and ERD pages live in docs/ (#16, #17)
- [ ] ERD reviewed and signed off by Hayk and Davit (#17)
- [ ] Service-based folder structure finalised and merged into `master` (#18)
- [ ] Contribution rules defined and published in this document (#19)
- [ ] All M2 PRs reviewed and merged by Anna (#21)
- [ ] Merged feature branches deleted (#22)

### Database (`db`) — Hayk

- [ ] `db` branch created and pushed to remote (#23)
- [ ] `db` Docker container defined and running via `docker-compose up db` (#24)
- [ ] PostgreSQL schema deployed based on the PM-approved ERD (#25, #26)
- [ ] All tables, keys, relationships, and constraints implemented (#26)
- [ ] Python connection to PostgreSQL verified and tested (#27)
- [ ] UCI Online Retail II data loaded into `raw_transactions` and `customers` tables; row counts validated (#28)
- [ ] Reusable CRUD helper methods written: `insert_customer`, `log_interaction`, `get_model_state`, `update_model_state` (#29)
- [ ] All utilities documented with clear docstrings (#30)
- [ ] PR opened from `db` → `master` and tagged for Anna's review (#31)

### Data Science (`ds`) — Davit

- [ ] `ds` branch created and pushed to remote (#32)
- [ ] `ds` Docker containers (`etl`, `model`) defined in `docker-compose.yml` (#33)
- [ ] EDA complete: missing fields, quality issues, and modelling opportunities identified and documented (#34)
- [ ] Hybrid data strategy implemented: UCI data for customer context, simulated rewards documented as synthetic (#35)
- [ ] DS pipeline uses Hayk's CRUD helpers — no direct local file reads in production code (#36)
- [ ] LinUCB algorithm implemented in NumPy: A matrix, b vector, θ update, UCB score per arm (#37–#38)
- [ ] Simulation engine functional: runs N rounds, logs interactions to DB, updates model state (#39)
- [ ] PR opened from `ds` → `master` and tagged for Anna's review (#40)

### Orchestration — *(Shared)*

- [ ] Repository reviewed; overall architecture and service dependencies understood (#11)
- [ ] Prefect research complete; short proposal written on how it fits the project (#12)
- [ ] Alignment with PM, DB, and DS on which steps become automated flows (#13)
- [ ] Orchestration plan written: which jobs are manual now, which are automated in M3+ (#14)
- [ ] Draft folder/service plan for the `orchestration/` component created (#15)

### Backend & Frontend — Victoria & Armine

> M2 focus is DB and DS. Backend and Frontend are primary M3 deliverables.

- [ ] `backend` branch pulled and local environment set up
- [ ] `frontend` branch pulled and local environment set up
- [ ] Architecture reviewed and any M3 blockers raised in Slack by April 20