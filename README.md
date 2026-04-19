# CampX — Campaign Optimization Engine

**DS 223 · Marketing Analytics · Group 1 · Spring 2026 · AUA**

A contextual bandit system (LinUCB) that selects the optimal promotional
action for each fashion retail customer — learning which offer maximises
net profit for which customer profile, updating after every interaction.

---

## Team

| Role | Member | Branch |
|------|--------|--------|
| PM | Anna Asatryan | `pm/main` |
| DB Developer | Hayk Alekyan | `db` |
| Backend | Victoria Makaryan | `backend` |
| Frontend | Armine Babajanyan | `frontend` |
| Data Scientist | Davit Badalyan | `ds` |
| Orchestration | *(shared)* | `orchestration` |

---

## Quick start

1. **Setup environment variables:**
```bash
cp .env.example .env
```

2. **Launch services:**
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

## Synthetic data generation

Generate a standalone synthetic dataset before any DB integration:

```bash
python3 generate_synthetic_data.py --n-customers 500 --n-rounds 5000 --random-seed 42 --output-dir outputs/synthetic_data
```

Persist the same generated artifacts through the DB developer's CRUD layer:

```bash
python3 generate_synthetic_data.py --n-customers 500 --n-rounds 5000 --persist-db --db-notes "initial DS integration load"
```

This writes:

- `customers.csv`
- `customer_latents.csv`
- `actions.csv`
- `interactions.csv`
- `model_state.csv`

It also writes validation artifacts in the same folder:

- `segment_counts.csv`
- `action_summary.csv`
- `customer_feature_summary.csv`
- `latent_feature_correlations.csv`
- `target_moment_comparison.csv`
- `monotonicity_checks.csv`
- `validation_report.txt`
- `sanity_checks.json`
- `metadata.json`
- `calibration.json`

The generator uses latent customer traits to create noisy observable RFM-style
features, assigns segments from observed features only, and simulates
action-level conversions and rewards under `random_policy` or a
`bandit_scaffold` placeholder mode.

The full calibration now lives in `ds/synthetic/config.py`, including:

- latent priors
- feature-generation coefficients
- action-response and revenue coefficients
- target moments for segment mix, mean AOV, conversion rates, and revenue ranges
- monotonicity thresholds checked during validation and tests

Run the generator regression tests with:

```bash
python3 -m unittest discover -s tests
```

Create an initial EDA report from the generated CSVs:

```bash
python3 generate_eda_report.py --input-dir outputs/synthetic_data
```

By default this writes summary tables, PNG charts, and a short Markdown report
to `outputs/synthetic_data/eda/`.

Compare simple baseline policies against the synthetic environment:

```bash
python3 run_baseline_comparison.py --n-customers 500 --train-rounds 5000 --eval-rounds 5000 --output-dir outputs/baselines
```

This writes:

- `policy_summary.csv`
- `policy_action_distribution.csv`
- `policy_round_traces.csv`
- `training_action_summary.csv`
- `policy_mapping.csv`
- `linear_model_coefficients.csv`
- `cumulative_reward_by_policy.png`
- `total_reward_by_policy.png`
- `action_mix_by_policy.png`
- `baseline_report.md`

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
├── .env.example          # Template for environment variables (committed)
└── .gitignore          
```

---

## Branching

```
One branch per role. Push directly to your branch, open one PR to main when ready.
main  (protected — Anna merges here)
├── pm
├── db
├── backend
├── frontend
├── ds
└── orchestration
```

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
