# Data Science & Modeling

**Owner:** Davit Badalyan · Branch: `ds`

---

## Overview

The final DS model is **LinUCB**: a contextual bandit that chooses one
promotion for each customer, observes the realized business reward, and updates
the selected action arm online.

For each customer context vector `x` and action `a`, the model computes:

```text
UCB_score(a) = theta_a.T @ x + alpha * sqrt(x.T @ A_a^-1 @ x)
```

The first term is exploitation: the current reward estimate. The second term is
exploration: an uncertainty bonus that shrinks as an action receives feedback.

The detailed feature and reward contract is in
[DS Feature & Reward Spec](ds_data_spec.md).

---

## Implemented Pipeline

The DS pipeline is fully synthetic and repeatable from scripts.

```text
campx/ds/synthetic/pipeline.py
  -> generate_latent_traits(...)
  -> generate_observed_features(...)
  -> assign_segments(...)
  -> simulate_interactions(...)
       - random_policy: uniform random actions
       - linucb: online LinUCB action selection and update
       - bandit_scaffold: backward-compatible alias for linucb
  -> build_validation_artifacts(...)
  -> export_artifacts(...)
```

Main entrypoint:

```bash
python -m campx.ds.generate_synthetic_data \
  --n-customers 500 \
  --n-rounds 5000 \
  --policy-mode linucb \
  --output-dir outputs/synthetic_data
```

The same code also works inside the DS container through `python main.py`.

---

## Feature Engineering

The model-visible customer context has exactly six observed features, defined
centrally in [campx/ds/synthetic/config.py](../campx/ds/synthetic/config.py):

| Feature | Unit | Model role | Signal |
|---------|------|------------|--------|
| `recency` | days | context | Lower means more recent engagement |
| `frequency` | purchase count | context | Higher means stronger repeat engagement |
| `monetary` | GBP-like currency | context | Higher means greater customer value |
| `basket_diversity` | category breadth score | context | Higher means broader shopping behavior |
| `avg_order_size` | GBP-like currency | context | Higher means larger baskets or premium buying |
| `purchase_regularity` | normalized cadence score | context | Higher means steadier repeat behavior |

Executable feature helpers live in
[campx/ds/synthetic/features.py](../campx/ds/synthetic/features.py):

- `get_model_feature_metadata()` returns the feature metadata.
- `get_model_feature_frame(customers)` validates and orders model-visible
  columns.
- `build_context_matrix(customers)` returns the numeric context matrix used by
  LinUCB and baseline models.

The helper enforces that all model features are present, numeric, finite, and in
the canonical order. It deliberately excludes identifiers, segments, latent
traits, conversion probabilities, and realized outcomes.

### Feature Scaling

LinUCB receives the six observed features after max scaling by the generated
customer pool. This keeps the six-feature context contract intact while
preventing raw monetary values from dominating the linear algebra.

The exported `model_state.csv` records:

- `feature_columns_json`
- `feature_means_json`
- `feature_scales_json`
- `context_encoding`

For the current model, `context_encoding` is:

```text
max_scaled_observed_features
```

---

## Synthetic Data Generation

The generator uses two-channel consistency:

1. latent traits generate observed customer behavior
2. the same latent traits drive action response

Latent traits are stored for validation and debugging only:

| Trait | Prior | Drives |
|-------|-------|--------|
| `z_price_sensitivity` | `Beta(2, 5)` | discount and shipping response |
| `z_brand_loyalty` | `Beta(3, 3)` | repeat behavior and organic conversion |
| `z_impulse_tendency` | `Beta(2, 4)` | recommendation and bundle response |

The model never receives these latent traits as inputs.

Observed features are generated in
[campx/ds/synthetic/features.py](../campx/ds/synthetic/features.py), with
calibration constants in
[campx/ds/synthetic/config.py](../campx/ds/synthetic/config.py).

---

## LinUCB Model

The LinUCB implementation lives in
[campx/ds/linucb.py](../campx/ds/linucb.py).

Each action has its own ridge-regression state:

```text
A_a = identity matrix at initialization
b_a = zero vector at initialization
theta_a = A_a^-1 b_a
```

For every simulated round:

1. sample a customer by purchase propensity
2. build the six-feature context vector `x`
3. score all actions with LinUCB
4. select the highest-UCB action
5. simulate conversion, revenue, cost, and reward
6. update only the selected action:

```text
A_a <- A_a + x x.T
b_a <- b_a + reward * x
theta_a <- A_a^-1 b_a
```

The simulator performs a small warm start so every action receives initial
feedback before pure UCB selection takes over. This avoids early collapse from
one lucky first action and gives every arm an initial reward signal.

---

## Reward Target

The optimization target is realized business reward:

```text
reward = revenue - cost
```

This is the primary metric because conversion alone ignores margin, and revenue
alone ignores promotion spend.

---

## Baselines

Baseline comparison logic lives in
[campx/ds/baselines.py](../campx/ds/baselines.py). It uses the same
`build_context_matrix(...)` helper for model-facing features.

Implemented baselines:

| Policy | Purpose |
|--------|---------|
| `random_uniform` | no-intelligence control |
| `best_historical_action` | one global best historical action |
| `segment_heuristic` | hand-written marketing rules |
| `segment_reward_lookup` | empirical segment-to-action lookup |
| `linear_reward_model` | supervised per-action ridge reward model |

Run:

```bash
python -m campx.ds.run_baseline_comparison \
  --n-customers 500 \
  --train-rounds 5000 \
  --eval-rounds 5000 \
  --output-dir outputs/baselines
```

---

## Exported Artifacts

A synthetic generation run writes:

| File | Purpose |
|------|---------|
| `customers.csv` | observed customer table |
| `customer_latents.csv` | debug-only latent traits |
| `actions.csv` | action metadata |
| `interactions.csv` | decisions, outcomes, rewards, and UCB score components |
| `model_state.csv` | per-action LinUCB state |
| `validation_report.txt` | run-level sanity report |
| `target_moment_comparison.csv` | calibration target checks |
| `monotonicity_checks.csv` | directional assumption checks |

For LinUCB runs, `interactions.csv` includes:

- `exploit_score`
- `explore_score`
- `ucb_score`

For random-policy runs, these score columns are present but empty.

---

## Evaluation Metrics

| Metric | Definition |
|--------|------------|
| Total reward | sum of `reward`; primary business metric |
| Mean reward | average `reward` per round |
| Conversion rate | average of `converted`; diagnostic |
| Action distribution | pull count and share per action |
| Model state | final `theta`, `A`, `b`, and `n_pulls` per action |

On a 500-customer, 5000-round seed-42 run, LinUCB produced total reward
`140475.41` versus `98783.84` for the same-scale random policy run.
