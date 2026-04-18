# Database — PostgreSQL

**Owner:** Hayk Alekyan · Branch: `db`

---

## Schema overview

The database has six tables supporting the full LinUCB pipeline.

| Table | Purpose |
|-------|---------|
| `raw_transactions` | Source data from UCI Online Retail — used to derive RFM features |
| `customers` | One row per customer, stores computed context features |
| `actions` | The 5 promotional arms the bandit chooses from |
| `interactions` | Log of every (customer, action, reward) bandit step |
| `model_state` | Persisted LinUCB matrices (A, b, θ) per action |
| `simulations` | Metadata for each simulation run |

---

## ERD

*(See ERD validated with PM and Data Scientist — diagram in milestone2/ folder)*

---

## Setup

```bash
docker-compose up db
```

The `init.sql` script runs automatically on first container start and creates all tables, seeds actions, and creates indexes.

---

## Connection

```python
import psycopg2, os
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", 5432),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)
```

---

## CRUD helpers

*(To be documented by Hayk — see `db/` folder)*