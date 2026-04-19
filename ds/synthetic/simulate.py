"""Interaction simulation for synthetic retail personalization data."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .actions import ActionDefinition
from .config import FEATURE_COLUMNS, SyntheticDataConfig


def simulate_interactions(
    customers: pd.DataFrame,
    latents: pd.DataFrame,
    actions: tuple[ActionDefinition, ...],
    config: SyntheticDataConfig,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate round-by-round interactions under the selected policy."""

    customer_frame = customers.merge(latents, on="customer_id", how="inner")
    sampled_customers = sample_customer_rounds(customer_frame, config.n_rounds, rng)
    action_ids = choose_actions(sampled_customers, actions, config, rng)
    round_numbers = np.arange(1, config.n_rounds + 1, dtype=int)

    p_convert = compute_conversion_probabilities(action_ids, sampled_customers)
    converted = rng.random(config.n_rounds) < p_convert

    revenue = simulate_revenue(
        sampled_customers=sampled_customers,
        action_ids=action_ids,
        actions=actions,
        round_numbers=round_numbers,
        converted=converted,
        rng=rng,
    )
    cost = compute_realized_costs(action_ids, revenue, converted)
    reward = revenue - cost

    interactions = pd.DataFrame(
        {
            "interaction_id": np.arange(1, config.n_rounds + 1, dtype=int),
            "round_number": round_numbers,
            "customer_id": sampled_customers["customer_id"].astype(int).to_numpy(),
            "action_id": action_ids.astype(int),
            "converted": converted.astype(bool),
            "revenue": revenue,
            "cost": cost,
            "reward": reward,
            "p_convert": p_convert,
            "simulation_id": config.simulation_id,
        }
    ).round({"revenue": 2, "cost": 2, "reward": 2, "p_convert": 4})

    model_state = initialize_model_state(actions, config)
    return interactions, model_state


def sample_customer_rounds(
    customer_frame: pd.DataFrame, n_rounds: int, rng: np.random.Generator
) -> pd.DataFrame:
    """Sample customers with replacement, weighted by purchase frequency."""

    weights = customer_frame["frequency"].astype(float).to_numpy() + 1.0
    probabilities = weights / weights.sum()
    sampled_indices = rng.choice(customer_frame.index.to_numpy(), size=n_rounds, p=probabilities)
    return customer_frame.loc[sampled_indices].reset_index(drop=True)


def choose_actions(
    sampled_customers: pd.DataFrame,
    actions: tuple[ActionDefinition, ...],
    config: SyntheticDataConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Choose actions for each round."""

    action_ids = np.array([action.action_id for action in actions], dtype=int)

    if config.policy_mode == "random_policy":
        return rng.choice(action_ids, size=len(sampled_customers), replace=True)

    # Placeholder until online bandit selection is implemented.
    return rng.choice(action_ids, size=len(sampled_customers), replace=True)


def compute_conversion_probabilities(
    action_ids: np.ndarray, sampled_customers: pd.DataFrame
) -> np.ndarray:
    """Compute action-specific conversion probabilities from latent traits."""

    price = sampled_customers["z_price_sensitivity"].to_numpy()
    loyalty = sampled_customers["z_brand_loyalty"].to_numpy()
    impulse = sampled_customers["z_impulse_tendency"].to_numpy()

    logits = np.zeros(len(sampled_customers), dtype=float)

    mask = action_ids == 0
    logits[mask] = -2.2 + 3.1 * loyalty[mask] - 0.3 * price[mask]

    mask = action_ids == 1
    logits[mask] = -1.9 + 3.4 * price[mask] - 1.6 * loyalty[mask] + 0.4 * impulse[mask]

    mask = action_ids == 2
    logits[mask] = -1.8 + 2.5 * price[mask] - 1.4 * impulse[mask] + 0.3 * loyalty[mask]

    mask = action_ids == 3
    logits[mask] = -2.3 + 2.1 * loyalty[mask] + 1.6 * impulse[mask]

    mask = action_ids == 4
    logits[mask] = -2.35 + 2.5 * impulse[mask] + 1.0 * loyalty[mask] + 0.4 * price[mask]

    probabilities = 1.0 / (1.0 + np.exp(-logits))
    return np.clip(probabilities, 0.02, 0.90)


def simulate_revenue(
    sampled_customers: pd.DataFrame,
    action_ids: np.ndarray,
    actions: tuple[ActionDefinition, ...],
    round_numbers: np.ndarray,
    converted: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Simulate gross merchandise revenue when a conversion occurs."""

    action_lookup = {action.action_id: action for action in actions}

    avg_order = sampled_customers["avg_order_size"].to_numpy()
    loyalty = sampled_customers["z_brand_loyalty"].to_numpy()
    price = sampled_customers["z_price_sensitivity"].to_numpy()
    impulse = sampled_customers["z_impulse_tendency"].to_numpy()
    basket_diversity = sampled_customers["basket_diversity"].to_numpy()

    seasonality = 1.0 + 0.08 * np.sin(2.0 * np.pi * (round_numbers - 1) / 52.0)
    base_basket = avg_order * np.clip(rng.normal(1.0, 0.10, size=len(sampled_customers)), 0.75, 1.35)

    revenue = np.zeros(len(sampled_customers), dtype=float)
    for action_id, action in action_lookup.items():
        mask = action_ids == action_id
        if not np.any(mask):
            continue

        multiplier = np.ones(mask.sum(), dtype=float) * action.revenue_multiplier
        if action_id == 0:
            multiplier += 0.05 * loyalty[mask]
        elif action_id == 1:
            multiplier += 0.10 * price[mask]
        elif action_id == 2:
            multiplier += 0.06 * price[mask] + 0.03 * (1.0 - impulse[mask])
        elif action_id == 3:
            multiplier += 0.08 * loyalty[mask] + 0.06 * impulse[mask]
        elif action_id == 4:
            multiplier += 0.18 * impulse[mask] + 0.04 * basket_diversity[mask]

        raw_revenue = (
            base_basket[mask]
            * multiplier
            * seasonality[mask]
            * np.clip(
                rng.normal(1.0, action.revenue_noise, size=mask.sum()),
                0.70,
                1.45,
            )
        )
        revenue[mask] = np.clip(raw_revenue, 15.0, action.max_revenue)

    revenue = np.where(converted, revenue, 0.0)
    return revenue


def compute_realized_costs(
    action_ids: np.ndarray, revenue: np.ndarray, converted: np.ndarray
) -> np.ndarray:
    """Compute realized action cost for each interaction."""

    costs = np.zeros(len(action_ids), dtype=float)

    mask = action_ids == 1
    costs[mask] = np.where(
        converted[mask],
        np.maximum(0.10 * revenue[mask], 4.00),
        0.10,
    )

    mask = action_ids == 2
    costs[mask] = np.where(converted[mask], 4.99, 0.10)

    mask = action_ids == 3
    costs[mask] = 0.30

    mask = action_ids == 4
    costs[mask] = np.where(converted[mask], 9.00, 0.20)

    return costs


def initialize_model_state(
    actions: tuple[ActionDefinition, ...], config: SyntheticDataConfig
) -> pd.DataFrame:
    """Create a schema-ready placeholder for later LinUCB state persistence."""

    context_dim = len(FEATURE_COLUMNS)
    theta = [0.0] * context_dim
    b_vector = [0.0] * context_dim
    a_matrix = np.eye(context_dim).tolist()

    rows = []
    for action in actions:
        rows.append(
            {
                "simulation_id": config.simulation_id,
                "policy_mode": config.policy_mode,
                "action_id": action.action_id,
                "action_name": action.action_name,
                "alpha": config.alpha,
                "context_dim": context_dim,
                "n_pulls": 0,
                "theta_json": json.dumps(theta),
                "a_json": json.dumps(a_matrix),
                "b_json": json.dumps(b_vector),
            }
        )

    return pd.DataFrame(rows)
