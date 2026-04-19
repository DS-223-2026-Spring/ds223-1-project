# Database — PostgreSQL

**Owner:** Hayk Alekyan · Branch: `db`

---

## Schema overview

Eight tables in two layers.

**Simulation layer** — generated once before bandit runs:

| Table | Purpose |
|-------|---------|
| `customers` | One row per simulated customer — RFM context vector for LinUCB |
| `customer_latents` | Debug only — latent traits that generated RFM and drive conversion |
| `products` | Static fashion product catalog — used by A3 and A4 actions |
| `bundles` | Pre-defined outfit bundles — used by bundle_offer action |

**Bandit layer** — grows during simulation:

| Table | Purpose |
|-------|---------|
| `actions` | 5 promotional arms — static, seeded once |
| `simulations` | One row per experiment run |
| `interactions` | Every (customer, action, reward) decision — core training log |
| `model_state` | LinUCB A, b, θ per action — persists across container restarts |

---

## Time dimension in `interactions`

Three timestamps capture the real-time decision → outcome gap:

decision_at   ← when the system assigned the action (email sent)
│
│  [conversion_window_hours — default 48h]
│
converted_at  ← when purchase occurred (NULL until observed)
observed_at   ← when model received outcome and updated

`converted`, `revenue`, `reward` are NULL until `observed_at` is set.
Prefect Flow 3 (outcome_observer) closes these pending rows after the window elapses.

---

## Setup

```bash
docker-compose up db pgadmin
```

Schema initialises automatically from `db/init.sql`.
Verify at http://localhost:5050 — login: admin@admin.com / admin123.

---

## CRUD helpers (`db/crud.py`)

All DB access goes through these helpers. No raw SQL elsewhere.

```python
# Customers
get_all_customers()
get_customer_by_id(customer_id)
get_customer_latents(customer_id)
insert_customer(**fields)
insert_customer_latent(customer_id, z_price_sensitivity, z_brand_loyalty, z_impulse_tendency)

# Interactions
log_interaction(simulation_id, customer_id, action_id, round_number, context_vector_bytes, ucb_score, cost)
observe_outcome(interaction_id, converted, revenue, converted_at, observed_at)
get_pending_interactions(older_than_hours=48)

# Model state
get_model_state(simulation_id, action_id)
upsert_model_state(simulation_id, action_id, round_number, n_pulls, theta_bytes, a_bytes, b_bytes, alpha)

# Simulations
create_simulation(sim_name, num_rounds, num_customers, alpha, ...)
complete_simulation(simulation_id)
```