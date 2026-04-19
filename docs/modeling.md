# Data Science & Modeling

**Owner:** Davit Badalyan · Branch: `ds`

---

## Overview

The core model is **LinUCB** (Linear Upper Confidence Bound), a contextual bandit that:

1. Takes a customer's context vector **x** (6 RFM features)
2. For each action *a*, computes: **θₐᵀx + α√(xᵀAₐ⁻¹x)**
3. Selects the action with the highest score
4. Observes the reward (revenue − cost)
5. Updates **Aₐ** and **bₐ** matrices for the chosen arm

The detailed DS data contract for features, leakage rules, simulator
assumptions, and reward definition is documented separately in
[DS Feature & Reward Spec](ds_data_spec.md).

---

## Data strategy — fully simulated

No external dataset. All customer data is generated from scratch using
a latent generative model.

**Why simulation?**
Running a real contextual bandit requires a live system with real customers
making real purchases in response to real promotions — data no academic
project can ethically collect. Simulation is the standard evaluation
approach in bandit research and is how the original LinUCB paper was
evaluated (Li et al., 2010).

**What makes this simulation honest:**
The latent traits that generate observable RFM features are the same
traits that drive action-specific conversion probability. The model
never sees the latents — only the noisy RFM proxies. This is what
makes the learning problem non-trivial and realistic.

---

## Latent generative model

Each customer has **L latent traits** drawn once at generation time
and anchored permanently to their `customer_id`.

In the current implementation L=3:

| Trait | Distribution | Drives |
|-------|-------------|--------|
| `z_brand_loyalty` | Beta(α, β) | Purchase frequency, recency, baseline conversion |
| `z_price_sensitivity` | Beta(α, β) | Response to discount and free shipping |
| `z_impulse_tendency` | Beta(α, β) | Response to bundle and recommendation |

Distribution parameters are configurable in `.env`.

**Two-channel consistency — the key design rule:**
The same `z` that generates RFM (channel 1 — observable history) also
drives conversion probability (channel 2 — action response), bound by
`customer_id`. Swapping latents between customers breaks both channels
simultaneously, making the assignment internally verified.

---

## Customer generation (`ds/etl.py`)

```python
# L latent traits drawn ONCE per customer — never re-drawn
z_loyalty = rng.beta(LOYALTY_ALPHA, LOYALTY_BETA, N)
z_price   = rng.beta(PRICE_ALPHA,   PRICE_BETA,   N)
z_impulse = rng.beta(IMPULSE_ALPHA, IMPULSE_BETA, N)

# RFM derived from SAME latents — two-channel consistency
frequency  = rng.poisson(2 + 10 * z_loyalty)
recency    = rng.exponential(30 / (0.1 + 0.9 * z_loyalty))
monetary   = frequency * rng.normal(55 + 30 * z_loyalty, 12)
```

---

## Conversion model (`ds/model.py`)

Action-specific sigmoid formulas over latent traits.
All coefficients are **explicit assumptions** documented here.

| Action | Formula | Primary driver |
|--------|---------|---------------|
| `no_action` | σ(2.5·z_l − 2.0) | Brand loyalty |
| `discount_10` | σ(3.0·z_p − 1.5·z_l − 1.0) | Price sensitivity |
| `free_shipping` | σ(2.0·z_p·(1−z_i) − 0.5) | Sensitivity × planning |
| `product_rec` | σ(2.0·z_l + 1.5·z_i − 1.5) | Loyalty + impulse |
| `bundle_offer` | σ(2.5·z_i + 0.8·z_l − 1.5·(1−z_p)) | Impulse tendency |

---

## LinUCB algorithm

Per-action ridge regression with UCB exploration bonus.
Reference: Li et al. (2010), *A Contextual-Bandit Approach to
Personalized News Article Recommendation*, WWW 2010.

```
UCB_score(a) = θₐᵀx + α · √(xᵀAₐ⁻¹x)
──────   ────────────────
exploit    explore bonus
(shrinks as Aₐ grows)

Update after observing reward r:
Aₐ ← Aₐ + xxᵀ
bₐ ← bₐ + r · x
θₐ ← Aₐ⁻¹bₐ
```

---

## Service pipeline (`ds/`)

```
ds/
├── Dockerfile
├── main.py
├── etl.py
└── model.py
```

---

## Baseline policies

| Policy | Description |
|--------|-------------|
| Random | Uniform random — zero-intelligence baseline |
| Heuristic | Static segment rules — represents traditional marketing |
| LinUCB | Learned contextual policy — should outperform both |

---

## Key parameters

| Parameter | Env var | Default | Description |
|-----------|---------|---------|-------------|
| `alpha` | `ALPHA` | 0.5 | Exploration–exploitation tradeoff |
| `d` | — | 6 | Context vector dimension (fixed by RFM features) |
| `N_rounds` | `N_ROUNDS` | 5000 | Simulation rounds per run |
| `N_customers` | `N_CUSTOMERS` | 500 | Customer pool size |
| `seed` | `RANDOM_SEED` | 42 | Reproducibility |

---

## Evaluation

| Metric | Definition |
|--------|-----------|
| Cumulative reward | Sum of (revenue − cost) — primary metric |
| Per-step regret | Oracle reward minus chosen reward — should decrease |
| Action distribution | Proportion of each action over time |
| Conversion rate by action | Validates response heterogeneity learning |
| θ heatmap | Did the model learn the right feature weights per action? |
