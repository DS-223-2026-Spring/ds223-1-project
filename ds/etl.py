"""Synthetic customer ETL helpers for standalone data generation."""

from synthetic.features import assign_segments, generate_observed_features
from synthetic.latents import generate_latent_traits

__all__ = [
    "assign_segments",
    "generate_latent_traits",
    "generate_observed_features",
]
