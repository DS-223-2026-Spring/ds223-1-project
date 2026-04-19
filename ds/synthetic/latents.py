"""Latent customer trait generation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_latent_traits(n_customers: int, rng: np.random.Generator) -> pd.DataFrame:
    """Draw one latent vector per customer."""

    customer_ids = np.arange(1, n_customers + 1, dtype=int)

    return pd.DataFrame(
        {
            "customer_id": customer_ids,
            "z_price_sensitivity": rng.beta(2.0, 5.0, size=n_customers),
            "z_brand_loyalty": rng.beta(3.0, 3.0, size=n_customers),
            "z_impulse_tendency": rng.beta(2.0, 4.0, size=n_customers),
        }
    ).round(
        {
            "z_price_sensitivity": 4,
            "z_brand_loyalty": 4,
            "z_impulse_tendency": 4,
        }
    )
