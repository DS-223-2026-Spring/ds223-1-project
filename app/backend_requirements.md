# Backend Requirements

---

## What this document is

The frontend is already built as a skeleton with mock data. To make it actually work, the backend needs to provide a set of HTTP endpoints that return data in specific shapes. This document describes every endpoint the frontend will call, what it needs back, and where that data lives in the database.

If there is ever a conflict between this document and the frontend code, this document is correct — the frontend can be updated to match.

---

## How the frontend talks to the backend

The frontend is a Streamlit app running in the `front` container. The backend is a FastAPI app running in the `api` container. They communicate over HTTP inside the Docker network.

- Base URL from inside Docker: `http://api:8000`
- Base URL from your host machine (for testing in the browser): `http://localhost:8000`

The frontend reads the base URL from an environment variable called `API_URL`.

The actual switch from mock data to real API calls happens in one line in `app/bandit_utils.py`:

```python
USE_MOCKS = True  # change to False when endpoints are ready
```

So the goal is to build the endpoints described below, then flip that flag.

---


### Format

Everything is JSON. Content type is `application/json`.

### Timestamps

Always in ISO 8601 format, UTC, with a `Z` at the end:

```
"2026-04-21T10:15:00Z"
```

Not Unix timestamps. Not local time. The database stores `TIMESTAMP` without a timezone — the backend is responsible for adding the `Z` before sending.

### Money

Return monetary values as plain JSON numbers, with two decimals:

```json
"cumulative_reward": 3214.55
```


### Percentages and rates

Always floats between 0 and 1, not percentages:

```json
"conversion_rate": 0.23   // means 23%
```

The frontend converts to `23%` for display.

### Missing data

Use JSON `null`, not `0`, not an empty string, and don't omit the key. For example, a simulation that is still running has no `completed_at` yet, so:

```json
{
  "completed_at": null,
  "cumulative_reward": null
}
```

This lets the frontend distinguish "this run hasn't finished" from "this run made zero profit."

### Action names

The five actions are identified by their string keys — same keys used in `actions.action_name` in the database:

```
no_action
discount_10
free_shipping
product_recommendation
bundle_offer
```

The frontend turns these into display labels like "10% discount" or "Product recommendation" using its own lookup table. The API should only ever return the string key.

Note: `actions.action_id` in the database goes from 0 to 4 (see `db/3_initial_insert.sql`). The API should return the string key, not the number.

### Errors

When something goes wrong, return a JSON body with a consistent shape, and the matching HTTP status code:

```json
{
  "error": "not_found",
  "message": "Simulation 42 does not exist.",
  "code": 404
}
```

Error slugs the frontend recognizes:

| HTTP code | `error` slug | When to use |
|-----------|--------------|-------------|
| 400 | `bad_request` | Missing or invalid query parameters |
| 404 | `not_found` | The ID doesn't exist in the database |
| 409 | `conflict` | Duplicate name, or trying to do something that already happened |
| 422 | `validation_error` | Request body has the wrong shape |
| 500 | `internal_error` | Any unhandled exception |
| 503 | `service_unavailable` | Database is down or unreachable |

These can be discussed and changed if needed.


---

## The endpoints

Eight endpoints total. Seven are consumed by the frontend. One (`POST /feedback`) isn't called by the frontend directly but is documented here because it controls the lifecycle of data the frontend does see.

### 1. GET /simulations

**Who uses it:** Every page. The simulation selector dropdown appears in the sidebar and needs to list all runs.

**What it does:** Returns a list of all simulations — past and currently running.

**Request:** No parameters. Just `GET /simulations`.

**Response:** An array of simulation objects, newest first.

```json
[
  {
    "simulation_id": 3,
    "sim_name": "alpha_0.5_baseline",
    "num_rounds": 5000,
    "num_customers": 500,
    "alpha": 0.5,
    "context_dim": 6,
    "conversion_window_hours": 48,
    "notes": "first real run",
    "started_at": "2026-04-21T09:00:00Z",
    "completed_at": "2026-04-21T10:12:00Z",
    "status": "completed",
    "cumulative_reward": 3214.55,
    "rounds_completed": 5000
  }
]
```

**Where each field comes from:**

Most fields are just direct SELECTs from the `simulations` table: `simulation_id`, `sim_name`, `num_rounds`, `num_customers`, `alpha`, `context_dim`, `conversion_window_hours`, `notes`, `started_at`, `completed_at`.

Three fields need to be computed:

- `status` — if `completed_at IS NOT NULL`, return `"completed"`. Otherwise return `"running"`.
- `cumulative_reward` — `SELECT SUM(reward) FROM interactions WHERE simulation_id = X AND observed_at IS NOT NULL`. If the simulation is still running and has no observed rows yet, return `null`.
- `rounds_completed` — `SELECT COUNT(*) FROM interactions WHERE simulation_id = X`.

**Tables touched:** `simulations`, `interactions`.

---

### 2. POST /simulate

**Who uses it:** The launch form on the Create Simulation page.

**What it does:** Creates a new simulation record and triggers the Prefect flow that runs it.

**Request body:**

```json
{
  "sim_name": "alpha_0.5_baseline",
  "num_rounds": 5000,
  "num_customers": 500,
  "alpha": 0.5,
  "notes": "first real run"
}
```

**Validation rules:**

- `sim_name` — required string, 1–100 chars, must be unique across all simulations
- `num_rounds` — required integer, 100 to 50000
- `num_customers` — required integer, 50 to 10000
- `alpha` — required float, 0.0 to 2.0
- `notes` — optional string, up to 500 chars

If anything fails validation, return 422 with `error: "validation_error"`. If the name is a duplicate, return 409 with `error: "conflict"`.

**Response (HTTP 201):**

```json
{
  "simulation_id": 5,
  "sim_name": "alpha_0.5_baseline",
  "status": "queued",
  "started_at": "2026-04-21T11:30:00Z"
}
```

**What the backend needs to do:**

1. Insert a row into `simulations` with `completed_at = NULL` and `started_at = now()`.
2. Trigger the Prefect `decision_loop_flow` for the new `simulation_id`, asynchronously.
3. Return 201 immediately, without waiting for the simulation to finish.


**Tables touched:** `simulations`.

---

### 3. GET /metrics

**Who uses it:** Interaction page and Analytics page. This is the heaviest endpoint — it feeds every chart on both pages.

**What it does:** Returns all the aggregated numbers for one simulation in a single response. Bundling everything into one endpoint keeps the dashboard fast and avoids sending 6 requests per page load.

**Request:** `GET /metrics?simulation_id=3`

If `simulation_id` is missing, return 400. If it doesn't exist, return 404.

**Response:**

```json
{
  "simulation_id": 3,
  "status": "running",
  "rounds_completed": 847,
  "cumulative_reward": 3214.55,
  "avg_reward_per_round": 3.79,
  "pending_observations": 22,

  "cumulative_reward_series": [
    { "round": 1,   "linucb":   2.4, "random":   1.1, "heuristic":   1.8 },
    { "round": 100, "linucb": 340.2, "random": 180.5, "heuristic": 255.1 }
  ],

  "action_distribution": [
    { "round": 1, "action": "discount_10" },
    { "round": 2, "action": "free_shipping" }
  ],

  "conversion_by_action": [
    { "action": "no_action",              "conversion_rate": 0.28, "n_pulls": 110 },
    { "action": "discount_10",            "conversion_rate": 0.23, "n_pulls": 340 },
    { "action": "free_shipping",          "conversion_rate": 0.18, "n_pulls": 180 },
    { "action": "product_recommendation", "conversion_rate": 0.31, "n_pulls": 250 },
    { "action": "bundle_offer",           "conversion_rate": 0.21, "n_pulls": 120 }
  ],

  "recent_interactions": [
    {
      "interaction_id": 10001,
      "customer_id": 42,
      "action": "discount_10",
      "converted": true,
      "revenue": 72.50,
      "reward": 66.00,
      "decision_at": "2026-04-21T10:15:00Z",
      "observed_at": "2026-04-21T10:15:03Z"
    }
  ]
}
```

**How to compute each field:**

Top-level counters:

```sql
-- rounds_completed
SELECT COUNT(*) FROM interactions WHERE simulation_id = :id;

-- cumulative_reward
SELECT SUM(reward) FROM interactions
WHERE simulation_id = :id AND observed_at IS NOT NULL;

-- avg_reward_per_round
-- just cumulative_reward / rounds_completed in Python (handle divide-by-zero)

-- pending_observations
SELECT COUNT(*) FROM interactions
WHERE simulation_id = :id AND observed_at IS NULL;
```

The three arrays:

- `cumulative_reward_series` — running sum of `reward` over `round_number`, one column per policy. See the section below on baselines.
- `action_distribution` — one row per interaction: just `round_number` and the action name. The frontend aggregates client-side.
- `conversion_by_action` — grouped by action, showing the conversion rate and total pull count for each. Conversion rate is the average of `converted` (treated as 0/1), computed only on rows where `observed_at IS NOT NULL`. `n_pulls` is the total regardless.
- `recent_interactions` — the last 20 rows by `decision_at` descending. Pending rows (where `observed_at IS NULL`) are included too — `converted`, `revenue`, `reward` will just be null for those.

**Performance tip:** at 5000 rounds with 3 policies, `cumulative_reward_series` has 15000 points. If the response gets too big, we can add a `?sample_rate=10` parameter to return every 10th point. Not urgent for now.

**Tables touched:** `interactions`, `actions`, `simulations`.

---

### 4. GET /customers

**Who uses it:** Optional Customer Explorer page — not strictly required for M3 but the mocks are ready if you have time.

**What it does:** Returns the full list of customers with their RFM features.

**Request:** `GET /customers`

**Response:**

```json
[
  {
    "customer_id": 1,
    "segment_label": "Champion",
    "gender": "F",
    "recency": 12.3,
    "frequency": 8.0,
    "monetary": 452.10,
    "basket_diversity": 4.2,
    "avg_order_size": 3.1,
    "purchase_regularity": 14.5
  }
]
```

Every field comes straight from the `customers` table. Filtering is done client-side in the frontend — no need to add query parameters.

Reminder: per `db/1_schema.sql`, `segment_label` is always one of `"Champion"`, `"Loyal"`, `"At-Risk"`, `"Lost"` and `gender` is always `"M"` or `"F"`.

**Tables touched:** `customers`.

---

### 5. GET /customers/{customer_id}

**Who uses it:** Optional — the detail panel on the Customer Explorer page.

**What it does:** Returns one customer's profile, their interaction history, and (optionally, for debugging) their latent traits.

**Request:** `GET /customers/42` or `GET /customers/42?debug=true`

**Response:**

```json
{
  "customer_id": 42,
  "segment_label": "Champion",
  "gender": "F",
  "rfm": {
    "recency": 12.3,
    "frequency": 8.0,
    "monetary": 452.10,
    "basket_diversity": 4.2,
    "avg_order_size": 3.1,
    "purchase_regularity": 14.5
  },
  "interactions": [
    {
      "interaction_id": 10001,
      "simulation_id": 3,
      "action": "discount_10",
      "converted": true,
      "revenue": 72.50,
      "reward": 66.00,
      "decision_at": "2026-04-21T10:15:00Z",
      "observed_at": "2026-04-21T10:15:03Z"
    }
  ],
  "latents": {
    "z_price_sensitivity": 0.72,
    "z_brand_loyalty":     0.44,
    "z_impulse_tendency":  0.12
  }
}
```

**Important:** the `latents` object is only included when `?debug=true` is passed. Otherwise, don't include the `latents` key at all (not even as null). This protects the project's core assumption that LinUCB never observes latent traits — it only sees RFM features. The debug view is for instructor demos only.

**Tables touched:** `customers`, `interactions`, `actions`, `customer_latents` (only if `debug=true`).

---

### 6. GET /model/state

**Who uses it:** The Model page.

**What it does:** Returns the current state of LinUCB — the θ vectors it has learned, how many times each action has been pulled, and the alpha used.

**Request:** `GET /model/state?simulation_id=3`

**Response:**

```json
{
  "simulation_id": 3,
  "alpha": 0.5,
  "round_number": 847,
  "updated_at": "2026-04-21T10:15:03Z",

  "n_pulls": {
    "no_action":              110,
    "discount_10":            340,
    "free_shipping":          180,
    "product_recommendation": 250,
    "bundle_offer":           120
  },

  "theta": {
    "recency":             { "no_action":  0.12, "discount_10": -0.33, "free_shipping":  0.05, "product_recommendation":  0.21, "bundle_offer": -0.08 },
    "frequency":           { "no_action":  0.45, "discount_10": -0.10, "free_shipping":  0.15, "product_recommendation":  0.60, "bundle_offer":  0.22 },
    "monetary":            { "no_action":  0.30, "discount_10":  0.05, "free_shipping":  0.25, "product_recommendation":  0.40, "bundle_offer":  0.18 },
    "basket_diversity":    { "no_action":  0.08, "discount_10":  0.02, "free_shipping":  0.12, "product_recommendation":  0.18, "bundle_offer":  0.55 },
    "avg_order_size":      { "no_action":  0.15, "discount_10":  0.10, "free_shipping":  0.30, "product_recommendation":  0.20, "bundle_offer":  0.42 },
    "purchase_regularity": { "no_action":  0.22, "discount_10": -0.05, "free_shipping":  0.18, "product_recommendation":  0.35, "bundle_offer":  0.10 }
  }
}
```

**Important shape rule:** `theta` must be exactly 6 feature rows by 5 action columns. The frontend heatmap expects this exact shape and will break if any row or column is missing. The order of features should follow what's in `bandit_utils.RFM_FEATURES`:

```
recency, frequency, monetary, basket_diversity, avg_order_size, purchase_regularity
```

**The theta_vector bytea column:** this is stored as raw numpy bytes. To deserialize, do:

```python
import numpy as np
theta = np.frombuffer(row["theta_vector"], dtype="<f8")
# theta is now a length-6 numpy array in the feature order above
```

If the DS team is using a different dtype or byte order, this bit needs to change. Worth confirming with Davit before you wire this up.

**Tables touched:** `model_state`, `simulations`, `actions`.

---

### 7. POST /decide

**Who uses it:** The Model page uses it in "preview" mode — the user picks a customer, hits the button, and the page shows them what LinUCB would choose and why. In production, this endpoint also drives the actual simulation loop.

**What it does:** Computes UCB scores for a given customer across all 5 actions. If `preview=true`, it just returns the scores. If `preview=false`, it also writes a new row to `interactions` for the chosen action.

**Request:** `POST /decide?customer_id=42&simulation_id=3&preview=true`

**Response:** An array of 5 objects, sorted by `ucb_score` descending (best action first):

```json
[
  { "action": "discount_10",            "exploit": 2.1, "explore": 0.9, "ucb_score": 3.0, "cost": 6.50 },
  { "action": "bundle_offer",           "exploit": 1.8, "explore": 1.1, "ucb_score": 2.9, "cost": 9.00 },
  { "action": "product_recommendation", "exploit": 1.5, "explore": 1.2, "ucb_score": 2.7, "cost": 0.30 },
  { "action": "free_shipping",          "exploit": 1.2, "explore": 1.0, "ucb_score": 2.2, "cost": 4.99 },
  { "action": "no_action",              "exploit": 0.5, "explore": 1.5, "ucb_score": 2.0, "cost": 0.00 }
]
```

**What the fields mean:**

- `exploit` is `θₐᵀ · x` — the learned estimate of expected reward for this customer and this action
- `explore` is `α · √(xᵀ · Aₐ⁻¹ · x)` — the UCB bonus, bigger when uncertain, shrinks as the action gets pulled more
- `ucb_score` is just `exploit + explore` — the value LinUCB ranks on
- `cost` is the static cost from the `actions` table (included so the frontend doesn't need a separate lookup)

**Preview vs. production mode:**

- `preview=true`: just compute and return. Don't modify any table. Used on the Model page.
- `preview=false` (the default): compute, pick the highest-scoring action, insert a row into `interactions` with `decision_at = now()` and `observed_at = NULL`, then return the same array plus an `interaction_id` field with the newly-created ID.

**Tables touched:**

- `customers` (to read the context vector)
- `model_state` (to read θ and A for each action)
- `actions` (for costs)
- `interactions` (INSERT only in non-preview mode)

---

### 8. POST /feedback

**Who uses it:** Nobody on the frontend. This is called by the Prefect `observe_outcomes_flow` when an interaction's conversion window closes.

**Why it's documented here:** the frontend's `pending_observations` counter and the 3-timestamp lifecycle in `interactions` both depend on this endpoint working correctly. So it's worth having it all in one place.

**Request body:**

```json
{
  "interaction_id": 10001,
  "converted": true,
  "revenue": 72.50,
  "converted_at": "2026-04-21T10:15:02Z"
}
```

**Response:**

```json
{
  "interaction_id": 10001,
  "reward": 66.00,
  "observed_at": "2026-04-21T10:15:03Z",
  "model_updated": true
}
```

**What the backend does:**

1. UPDATE the `interactions` row: set `converted`, `revenue`, `converted_at`, and `observed_at = now()`.
2. Compute `reward = revenue - cost` and save it.
3. Run the LinUCB update for that action's arm: `Aₐ += xxᵀ`, `bₐ += r·x`, then `θₐ = Aₐ⁻¹bₐ`.
4. UPSERT the new state into `model_state` for that `(simulation_id, action_id)` pair, incrementing `round_number` and `n_pulls`.

If someone calls `/feedback` twice for the same `interaction_id`, return 409 with `error: "conflict"` — the second call shouldn't be allowed to overwrite the first.

**Tables touched:** `interactions` (UPDATE), `model_state` (UPSERT).

---

## How the data flows through `interactions`

Every interaction row goes through three stages, marked by three timestamps:

```
decision_at    — set when the row is first inserted (by POST /decide or
                 the decision_loop_flow). The action has been assigned
                 but no outcome is known yet.

   ... wait conversion_window_hours (default 48) ...

converted_at   — set when the customer actually buys (or the window closes
                 without a conversion). Can be NULL if no purchase happened.
observed_at    — set at the same time. Means the outcome is now known and
                 the model has been updated.
```

Until `observed_at` is filled in, the columns `converted`, `revenue`, `reward`, and `converted_at` are all `NULL`. The schema enforces this with a CHECK constraint:

```sql
CHECK (observed_at IS NOT NULL OR converted IS NULL)
```

When writing `/metrics` queries, the canonical filter for "this counts toward cumulative reward" is `observed_at IS NOT NULL`. The `pending_observations` counter is the opposite: `observed_at IS NULL`.

---

## Tables and columns the frontend uses

Quick reference — the columns each endpoint actually reads:

| Table | Columns | Used by |
|-------|---------|---------|
| `simulations` | `simulation_id`, `sim_name`, `num_rounds`, `num_customers`, `alpha`, `context_dim`, `conversion_window_hours`, `notes`, `started_at`, `completed_at` | /simulations, /simulate, /metrics |
| `customers` | `customer_id`, `gender`, `segment_label`, all 6 RFM columns | /customers, /customers/{id} |
| `customer_latents` | `z_price_sensitivity`, `z_brand_loyalty`, `z_impulse_tendency` | /customers/{id}?debug=true only |
| `actions` | `action_id`, `action_name`, `action_cost` | /metrics, /model/state, /decide |
| `interactions` | `interaction_id`, `customer_id`, `action_id`, `simulation_id`, `round_number`, `converted`, `revenue`, `cost`, `reward`, `decision_at`, `observed_at` | /metrics, /customers/{id} |
| `model_state` | `simulation_id`, `action_id`, `theta_vector`, `n_pulls`, `alpha`, `updated_at`, `round_number` | /model/state, /decide |


