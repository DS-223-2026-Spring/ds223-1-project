# Baseline Policy Comparison

- Customers per split: 500
- Training rounds: 5000
- Evaluation rounds: 5000
- Random seed: 42

## Evaluation Winner
- Best total reward: `linear_reward_model` with 142311.06
- Runner-up gap: 279.26 vs `best_historical_action`
- Best conversion rate among evaluated policies: linear_reward_model

## Training Data Snapshot
- Highest mean reward under random logged data: `bundle_offer` (28.02)

## Heuristic Policy Rules
- At-Risk: `free_shipping`
- Champion: `no_action`
- Lost: `discount_10`
- Loyal: `product_recommendation`

## Files
- `policy_summary.csv` and `policy_round_traces.csv` contain the main comparison outputs.
- `policy_mapping.csv` documents the static and learned segment rules.
- `linear_model_coefficients.csv` contains the per-action ridge coefficients.
