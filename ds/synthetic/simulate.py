"""Interaction simulation for synthetic retail personalization data."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import ActionCalibration, FEATURE_COLUMNS, SyntheticDataConfig


def simulate_interactions(
    customers: pd.DataFrame,
    latents: pd.DataFrame,
    actions: tuple[ActionCalibration, ...],
    config: SyntheticDataConfig,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate round-by-round interactions under the selected policy."""

    customer_frame = customers.merge(latents, on="customer_id", how="inner")
    sampled_customers = sample_customer_rounds(customer_frame, config.n_rounds, config, rng)
    action_ids = choose_actions(sampled_customers, actions, config, rng)
    round_numbers = np.arange(1, config.n_rounds + 1, dtype=int)

    p_convert = compute_conversion_probabilities(
        action_ids=action_ids,
        sampled_customers=sampled_customers,
        actions=actions,
        config=config,
    )
    converted = rng.random(config.n_rounds) < p_convert

    revenue = simulate_revenue(
        sampled_customers=sampled_customers,
        action_ids=action_ids,
        actions=actions,
        round_numbers=round_numbers,
        converted=converted,
        config=config,
        rng=rng,
    )
    cost = compute_realized_costs(
        action_ids=action_ids,
        revenue=revenue,
        converted=converted,
        actions=actions,
    )
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
    customer_frame: pd.DataFrame,
    n_rounds: int,
    config: SyntheticDataConfig,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Sample customers with replacement, weighted by purchase frequency."""

    sampling_cfg = config.calibration.simulation
    weights = (
        customer_frame["frequency"].astype(float).to_numpy()
        + sampling_cfg.sampling_frequency_offset
    )
    probabilities = weights / weights.sum()
    sampled_indices = rng.choice(
        customer_frame.index.to_numpy(),
        size=n_rounds,
        p=probabilities,
    )
    return customer_frame.loc[sampled_indices].reset_index(drop=True)


def choose_actions(
    sampled_customers: pd.DataFrame,
    actions: tuple[ActionCalibration, ...],
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
    action_ids: np.ndarray,
    sampled_customers: pd.DataFrame,
    actions: tuple[ActionCalibration, ...],
    config: SyntheticDataConfig,
) -> np.ndarray:
    """Compute action-specific conversion probabilities from latent traits."""

    price = sampled_customers["z_price_sensitivity"].to_numpy()
    loyalty = sampled_customers["z_brand_loyalty"].to_numpy()
    impulse = sampled_customers["z_impulse_tendency"].to_numpy()
    planner = 1.0 - impulse
    action_lookup = {action.action_id: action for action in actions}
    simulation_cfg = config.calibration.simulation

    logits = np.zeros(len(sampled_customers), dtype=float)
    for action_id, action in action_lookup.items():
        mask = action_ids == action_id
        if not np.any(mask):
            continue
        logits[mask] = (
            action.conversion_intercept
            + action.conversion_price_weight * price[mask]
            + action.conversion_loyalty_weight * loyalty[mask]
            + action.conversion_impulse_weight * impulse[mask]
            + action.conversion_planner_weight * planner[mask]
        )

    probabilities = 1.0 / (1.0 + np.exp(-logits))
    return np.clip(
        probabilities,
        simulation_cfg.p_convert_min,
        simulation_cfg.p_convert_max,
    )


def simulate_revenue(
    sampled_customers: pd.DataFrame,
    action_ids: np.ndarray,
    actions: tuple[ActionCalibration, ...],
    round_numbers: np.ndarray,
    converted: np.ndarray,
    config: SyntheticDataConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Simulate gross merchandise revenue when a conversion occurs."""

    action_lookup = {action.action_id: action for action in actions}
    simulation_cfg = config.calibration.simulation

    avg_order = sampled_customers["avg_order_size"].to_numpy()
    price = sampled_customers["z_price_sensitivity"].to_numpy()
    loyalty = sampled_customers["z_brand_loyalty"].to_numpy()
    impulse = sampled_customers["z_impulse_tendency"].to_numpy()
    planner = 1.0 - impulse
    basket_diversity = sampled_customers["basket_diversity"].to_numpy()

    seasonality = 1.0 + simulation_cfg.seasonality_amplitude * np.sin(
        2.0 * np.pi * (round_numbers - 1) / simulation_cfg.seasonality_period
    )
    base_basket = avg_order * np.clip(
        rng.normal(
            simulation_cfg.basket_noise_mean,
            simulation_cfg.basket_noise_sd,
            size=len(sampled_customers),
        ),
        simulation_cfg.basket_noise_min,
        simulation_cfg.basket_noise_max,
    )

    revenue = np.zeros(len(sampled_customers), dtype=float)
    for action_id, action in action_lookup.items():
        mask = action_ids == action_id
        if not np.any(mask):
            continue

        multiplier = (
            action.revenue_base_multiplier
            + action.revenue_price_weight * price[mask]
            + action.revenue_loyalty_weight * loyalty[mask]
            + action.revenue_impulse_weight * impulse[mask]
            + action.revenue_planner_weight * planner[mask]
            + action.revenue_basket_weight * basket_diversity[mask]
        )

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
    action_ids: np.ndarray,
    revenue: np.ndarray,
    converted: np.ndarray,
    actions: tuple[ActionCalibration, ...],
) -> np.ndarray:
    """Compute realized action cost for each interaction."""

    costs = np.zeros(len(action_ids), dtype=float)
    action_lookup = {action.action_id: action for action in actions}

    for action_id, action in action_lookup.items():
        mask = action_ids == action_id
        if not np.any(mask):
            continue

        converted_cost = np.maximum(
            action.converted_cost_rate * revenue[mask],
            action.converted_cost_floor,
        )
        costs[mask] = np.where(
            converted[mask],
            converted_cost,
            action.non_conversion_cost,
        )

    return costs


def initialize_model_state(
    actions: tuple[ActionCalibration, ...],
    config: SyntheticDataConfig,
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
