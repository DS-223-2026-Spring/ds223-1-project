# Data Science & Modeling

**Owner:** Davit Badalyan · Branch: `ds`

---

## Overview

The core model is **LinUCB** (Linear Upper Confidence Bound), a contextual bandit algorithm that:

1. Takes a customer's context vector **x** (RFM features + basket features)
2. For each action *a*, computes a score: **θₐᵀx + α√(xᵀAₐ⁻¹x)**
3. Selects the action with the highest score
4. Observes the reward (conversion × revenue − cost)
5. Updates **Aₐ** and **bₐ** matrices

---

## Data strategy

### Real data source
**UCI Online Retail II** — `https://archive.uci.edu/dataset/352/online+retail`

- ~500k UK e-commerce transactions (2009–2011)
- Used to compute realistic RFM + basket features per customer
- Load with: `from ucimlrepo import fetch_ucirepo; online_retail = fetch_ucirepo(id=352)`

### Simulated interactions
Since no real bandit interaction log exists, reward signals are simulated:

- Base conversion rates per action: `no_action=2%, discount_10=12%, free_shipping=9%, product_recommendation=7%, bundle_offer=10%`
- Reward = `converted × revenue − action_cost`
- Conversion probability is modulated by customer context (high-recency customers convert better)

---

## ETL pipeline (`ds/etl/`)

1. Fetch UCI data
2. Compute RFM + extended features
3. Load into `raw_transactions` and `customers` tables

## Model pipeline (`ds/model/`)

1. Load customer contexts from DB
2. Run N-round simulation using LinUCB
3. Persist updated model state to `model_state` table
4. Log all interactions to `interactions` table

---

## Key parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `alpha` | 0.5 | Exploration–exploitation tradeoff |
| `d` | 6 | Context vector dimension |
| `N_rounds` | configurable | Simulation rounds per run |