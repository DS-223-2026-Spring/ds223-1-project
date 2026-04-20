"""Observed feature generation from latent customer traits."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import GeneratorCalibration


def generate_observed_features(
    latents: pd.DataFrame,
    calibration: GeneratorCalibration,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Generate noisy RFM-style features from latent traits."""

    price = latents["z_price_sensitivity"].to_numpy()
    loyalty = latents["z_brand_loyalty"].to_numpy()
    impulse = latents["z_impulse_tendency"].to_numpy()
    n_customers = len(latents)
    feature_cfg = calibration.features

    frequency_rate = (
        feature_cfg.frequency_base
        + feature_cfg.frequency_loyalty_weight * loyalty
        + feature_cfg.frequency_impulse_weight * impulse
        + feature_cfg.frequency_price_relief_weight * (1.0 - price)
    )
    frequency = np.clip(
        rng.poisson(frequency_rate, size=n_customers),
        feature_cfg.frequency_min,
        feature_cfg.frequency_max,
    )

    recency_mean = (
        feature_cfg.recency_base
        + feature_cfg.recency_loyalty_curve_weight * np.square(1.0 - loyalty)
        + feature_cfg.recency_price_weight * price
        - feature_cfg.recency_impulse_weight * impulse
    )
    recency = np.clip(
        rng.gamma(
            shape=feature_cfg.recency_gamma_shape,
            scale=recency_mean / feature_cfg.recency_gamma_shape,
        ),
        feature_cfg.recency_min,
        feature_cfg.recency_max,
    )

    avg_order_size_mean = (
        feature_cfg.avg_order_base
        + feature_cfg.avg_order_impulse_weight * impulse
        + feature_cfg.avg_order_loyalty_weight * loyalty
        - feature_cfg.avg_order_price_weight * price
    )
    avg_order_size = np.clip(
        rng.normal(avg_order_size_mean, feature_cfg.avg_order_noise, size=n_customers),
        feature_cfg.avg_order_min,
        feature_cfg.avg_order_max,
    )

    basket_diversity = np.clip(
        rng.normal(
            feature_cfg.basket_diversity_base
            + feature_cfg.basket_diversity_impulse_weight * impulse
            + feature_cfg.basket_diversity_loyalty_weight * loyalty,
            feature_cfg.basket_diversity_noise,
            size=n_customers,
        ),
        feature_cfg.basket_diversity_min,
        feature_cfg.basket_diversity_max,
    )

    purchase_regularity = np.clip(
        feature_cfg.regularity_base
        + feature_cfg.regularity_loyalty_weight * loyalty
        - feature_cfg.regularity_impulse_weight * impulse
        + rng.normal(0.0, feature_cfg.regularity_noise, size=n_customers),
        feature_cfg.regularity_min,
        feature_cfg.regularity_max,
    )

    monetary_multiplier = np.clip(
        rng.normal(
            feature_cfg.monetary_multiplier_base
            + feature_cfg.monetary_multiplier_loyalty_weight * loyalty
            + feature_cfg.monetary_multiplier_impulse_weight * impulse
            - feature_cfg.monetary_multiplier_price_weight * price,
            feature_cfg.monetary_multiplier_noise,
            size=n_customers,
        ),
        feature_cfg.monetary_multiplier_min,
        feature_cfg.monetary_multiplier_max,
    )
    monetary = np.clip(
        frequency * avg_order_size * monetary_multiplier,
        feature_cfg.monetary_min,
        feature_cfg.monetary_max,
    )

    customers = pd.DataFrame(
        {
            "customer_id": latents["customer_id"].astype(int),
            "recency": np.rint(recency).astype(int),
            "frequency": frequency.astype(int),
            "monetary": monetary,
            "basket_diversity": basket_diversity,
            "avg_order_size": avg_order_size,
            "purchase_regularity": purchase_regularity,
        }
    )
    customers["segment"] = assign_segments(customers, calibration)

    return customers[
        [
            "customer_id",
            "segment",
            "recency",
            "frequency",
            "monetary",
            "basket_diversity",
            "avg_order_size",
            "purchase_regularity",
        ]
    ].round(
        {
            "monetary": 2,
            "basket_diversity": 2,
            "avg_order_size": 2,
            "purchase_regularity": 3,
        }
    )


def assign_segments(
    customers: pd.DataFrame,
    calibration: GeneratorCalibration,
) -> pd.Series:
    """Assign segments from observed features only."""

    segment_cfg = calibration.segments
    conditions = [
        (customers["recency"] < segment_cfg.champion_recency_max)
        & (customers["frequency"] >= segment_cfg.champion_frequency_min)
        & (customers["monetary"] > segment_cfg.champion_monetary_min),
        (customers["recency"] < segment_cfg.loyal_recency_max)
        & (customers["frequency"] >= segment_cfg.loyal_frequency_min),
        (customers["recency"] > segment_cfg.at_risk_recency_min)
        & (customers["frequency"] >= segment_cfg.at_risk_frequency_min),
    ]
    labels = ["Champion", "Loyal", "At-Risk"]
    segments = np.select(conditions, labels, default="Lost")
    return pd.Series(segments, index=customers.index, dtype="object")
