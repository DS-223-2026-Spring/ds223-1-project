"""Observed feature generation from latent customer traits."""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_observed_features(
    latents: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Generate noisy RFM-style features from latent traits."""

    price = latents["z_price_sensitivity"].to_numpy()
    loyalty = latents["z_brand_loyalty"].to_numpy()
    impulse = latents["z_impulse_tendency"].to_numpy()
    n_customers = len(latents)

    frequency_rate = 1.0 + 8.4 * loyalty + 1.5 * impulse + 0.9 * (1.0 - price)
    frequency = np.clip(rng.poisson(frequency_rate, size=n_customers), 1, 18)

    recency_mean = 16.0 + 125.0 * np.square(1.0 - loyalty) + 38.0 * price - 10.0 * impulse
    recency = np.clip(rng.gamma(shape=2.0, scale=recency_mean / 2.0), 1.0, 240.0)

    avg_order_size_mean = 40.0 + 34.0 * impulse + 24.0 * loyalty - 16.0 * price
    avg_order_size = np.clip(
        rng.normal(avg_order_size_mean, 8.0, size=n_customers),
        15.0,
        120.0,
    )

    basket_diversity = np.clip(
        rng.normal(1.4 + 4.2 * impulse + 1.1 * loyalty, 0.8, size=n_customers),
        1.0,
        8.0,
    )

    purchase_regularity = np.clip(
        0.18 + 0.70 * loyalty - 0.10 * impulse + rng.normal(0.0, 0.08, size=n_customers),
        0.02,
        0.99,
    )

    monetary_multiplier = np.clip(
        rng.normal(
            0.86 + 0.15 * loyalty + 0.09 * impulse - 0.10 * price,
            0.12,
            size=n_customers,
        ),
        0.55,
        1.35,
    )
    monetary = np.clip(frequency * avg_order_size * monetary_multiplier, 20.0, 2200.0)

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
    customers["segment"] = assign_segments(customers)

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


def assign_segments(customers: pd.DataFrame) -> pd.Series:
    """Assign segments from observed features only."""

    conditions = [
        (customers["recency"] < 30)
        & (customers["frequency"] >= 8)
        & (customers["monetary"] > 400),
        (customers["recency"] < 60) & (customers["frequency"] >= 4),
        (customers["recency"] > 90) & (customers["frequency"] >= 3),
    ]
    labels = ["Champion", "Loyal", "At-Risk"]
    segments = np.select(conditions, labels, default="Lost")
    return pd.Series(segments, index=customers.index, dtype="object")
