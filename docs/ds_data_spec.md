# DS Feature & Reward Spec

**Owner:** Davit Badalyan · Branch: `ds`

This document defines the model-facing features, the core synthetic-data
assumptions, and the target variable used for baseline models and the
contextual bandit.

---

## Purpose

The project is not predicting "who will convert" in isolation. The decision
problem is:

> given a customer context `x` and an action `a`, choose the action that
> maximizes expected net business value.

So the primary learning target is **reward**, not raw conversion.

---

## Model Inputs

The current customer context vector has **6 observed features**. These are the
only behavioral features intended to be visible to the bandit or baseline
models.

| Feature | Type | Unit / scale | Meaning | Intended signal |
|---------|------|--------------|---------|-----------------|
| `recency` | integer | days | Days since the customer's last purchase | Lower is better / more recent |
| `frequency` | integer | count | Number of purchases in the observation window | Higher indicates stronger engagement |
| `monetary` | float | GBP-like currency | Total spend in the observation window | Higher indicates customer value |
| `basket_diversity` | float | approx. item/category breadth score | How varied the customer's basket tends to be | Higher suggests broader shopping behavior |
| `avg_order_size` | float | GBP-like currency | Average value per order | Higher suggests larger baskets or premium buying |
| `purchase_regularity` | float | normalized `0..1` score | How steady the purchase cadence is | Higher suggests more consistent repeat behavior |

These feature names and metadata are defined centrally in
`campx/ds/synthetic/config.py`. The executable extraction helper is
`build_context_matrix(...)` in `campx/ds/synthetic/features.py`.

### Executable feature contract

Model-facing feature extraction must go through:

```python
from campx.ds.synthetic.features import build_context_matrix

x = build_context_matrix(customers)
```

The helper validates that all six model-visible columns are present, numeric,
finite, and ordered according to `FEATURE_COLUMNS`. This keeps LinUCB,
baseline models, and DB context-vector persistence aligned on the same feature
order.

LinUCB then max-scales the six observed features using the generated customer
pool. The model state exports this preprocessing as
`context_encoding = "max_scaled_observed_features"` plus JSON columns for the
feature order and scale values.

### Feature availability

- These 6 fields are the intended **model inputs**.
- `segment` is a derived marketing label and can be used for heuristics or
  reporting, but it is not the core continuous context representation.
- `customer_id` is an identifier only, not a predictive feature.
- `action_id` is part of the decision, not part of the customer context.

### Leakage rules

The following values must **not** be used as model inputs:

- latent traits from `customer_latents.csv`
  - `z_price_sensitivity`
  - `z_brand_loyalty`
  - `z_impulse_tendency`
- `p_convert`
  - this is simulator internals, not an observable business feature
- realized `revenue`, `cost`, `reward`, or `converted` from the current
  decision row before the decision is made

Those fields are valid for evaluation and debugging, but not as pre-decision
features.

---

## Feature-generation assumptions

The synthetic generator is built around **two-channel consistency**:

1. latent traits generate the observed customer behavior
2. the same latent traits also generate action response

This matters because otherwise the learning problem collapses into noise or
becomes trivially gameable.

### Latent traits

Each customer has three unobserved traits:

| Trait | Range | Prior | Interpretation |
|-------|-------|-------|----------------|
| `z_price_sensitivity` | `0..1` | `Beta(2, 5)` | More responsive to discounts and shipping friction |
| `z_brand_loyalty` | `0..1` | `Beta(3, 3)` | More likely to buy repeatedly and convert without heavy incentives |
| `z_impulse_tendency` | `0..1` | `Beta(2, 4)` | More likely to respond to recommendations and bundles |

The model never sees these values directly.

### Directional assumptions behind observed features

The generator enforces the following qualitative relationships:

- higher loyalty increases `frequency`
- higher loyalty lowers `recency`
- higher loyalty increases `monetary`
- higher loyalty increases `purchase_regularity`
- higher impulse increases `basket_diversity`
- higher impulse increases `avg_order_size`
- higher price sensitivity reduces spend and basket value on average

These relationships are implemented with noise so the features remain
imperfect proxies rather than deterministic copies of the latents.

### Segment assignment

Segments are derived from observed features only:

| Segment | Rule |
|---------|------|
| `Champion` | `recency < 30` and `frequency >= 8` and `monetary > 400` |
| `Loyal` | `recency < 60` and `frequency >= 4` |
| `At-Risk` | `recency > 90` and `frequency >= 3` |
| `Lost` | otherwise |

These segment rules live in `campx/ds/synthetic/config.py`.

### Action set

The canonical actions are:

| Action ID | Action name | Business interpretation |
|-----------|-------------|-------------------------|
| `0` | `no_action` | Control / organic conversion |
| `1` | `discount_10` | Margin-reducing discount for price-sensitive users |
| `2` | `free_shipping` | Shipping-friction relief |
| `3` | `product_recommendation` | Cheap personalization message |
| `4` | `bundle_offer` | Basket-expanding bundle promotion |

The exact action economics and simulator coefficients are defined in
`campx/ds/synthetic/config.py`.

---

## Target variable definition

### Primary target: `reward`

For the project goal, the main target is:

```text
reward = revenue - cost
```

This is the value optimized by the bandit and the main metric used in baseline
comparison.

Interpretation:

- `revenue` is realized gross merchandise value from a conversion
- `cost` is the action cost paid by the business
- a non-converting action can still have positive cost
- higher reward is better

Why this is the correct target:

- conversion alone ignores margin
- revenue alone ignores promotion spend
- reward directly aligns the model with business value

### Secondary target: `converted`

`converted` is a useful auxiliary outcome for reporting and sanity checks, but
it is **not** the main optimization target. A policy can improve conversion
while still reducing profit if it overuses expensive promotions.

### Optimization target vs observed label

There are two related concepts:

| Concept | Definition |
|---------|------------|
| optimization target | expected reward `E[reward | x, a]` |
| observed training label | realized one-step reward for the chosen action |

The contextual bandit never observes the counterfactual rewards for actions it
did not choose on that round. It only sees the realized reward for the chosen
action.

### Auxiliary simulator columns

Some exported columns are for diagnostics rather than model training:

| Column | Role |
|--------|------|
| `p_convert` | latent simulator probability used to sample conversion |
| `simulation_id` | run identifier |
| `round_number` | order of interactions within one simulation run |

---

## Baseline-model framing

The current baseline comparison script in `campx/ds/baselines.py` uses the
following framing:

- train on logged random-policy interactions
- use observed customer features plus chosen action
- compare policies by holdout **total reward**

Implemented baseline families:

| Policy | What it represents |
|--------|--------------------|
| `random_uniform` | no intelligence / control baseline |
| `best_historical_action` | one static action for everyone |
| `segment_heuristic` | hand-written marketing rules |
| `segment_reward_lookup` | segment-level empirical lookup |
| `linear_reward_model` | simple contextual supervised baseline |

For these baselines, the effective supervised label is still realized
**reward**, because that is the quantity aligned with the project goal.

---

## Assumptions and limitations

These assumptions are explicit and should be treated as part of the simulator
contract.

### Business assumptions

- retailer is online fashion, men and women, mid-market pricing
- typical product prices are about `£15` to `£120`
- mean average order value should be near `£65`
- some customers buy seasonally, while strong customers buy year-round
- promotions can increase conversion but may reduce margin

### Simulation assumptions

- one interaction produces one immediate reward outcome
- action effects are one-step and do not yet model long-term customer fatigue
  or carryover
- seasonality is present in simulated revenue
- customers are sampled by purchase propensity, not uniformly
- observed features are noisy proxies for latent preferences
- bundle offers should produce higher converted revenue than `no_action` on
  average

### Modeling limitations

- the environment is calibrated, not learned from real retailer data
- numeric coefficients are hand-tuned and stored centrally in
  `campx/ds/synthetic/config.py`
- offline baselines are evaluated in the same synthetic environment that
  generated the logged data
- current reward is immediate and does not include customer lifetime value

---

## Practical usage rules

When training or evaluating models in this repo:

- use only the 6 observed customer features as the default context vector
- optimize and compare on `reward`
- treat `converted` as a secondary diagnostic metric
- never train on latent traits or `p_convert`
- report both business metrics and behavior metrics
  - total reward
  - mean reward
  - conversion rate
  - action distribution

---

## Source of truth

This document explains the modeling contract in prose. The exact numeric
calibration lives in:

- `campx/ds/synthetic/config.py`
- `campx/ds/synthetic/features.py`
- `campx/ds/synthetic/simulate.py`
- `campx/ds/linucb.py`
