"""Latent customer trait generation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import GeneratorCalibration


def generate_latent_traits(
    n_customers: int,
    calibration: GeneratorCalibration,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Draw one latent vector per customer."""

    customer_ids = np.arange(1, n_customers + 1, dtype=int)
    priors = calibration.latents

    return pd.DataFrame(
        {
            "customer_id": customer_ids,
            "z_price_sensitivity": rng.beta(
                priors.price_sensitivity.alpha,
                priors.price_sensitivity.beta,
                size=n_customers,
            ),
            "z_brand_loyalty": rng.beta(
                priors.brand_loyalty.alpha,
                priors.brand_loyalty.beta,
                size=n_customers,
            ),
            "z_impulse_tendency": rng.beta(
                priors.impulse_tendency.alpha,
                priors.impulse_tendency.beta,
                size=n_customers,
            ),
        }
    ).round(
        {
            "z_price_sensitivity": 4,
            "z_brand_loyalty": 4,
            "z_impulse_tendency": 4,
        }
    )
