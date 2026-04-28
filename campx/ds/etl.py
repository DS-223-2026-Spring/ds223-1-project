"""Synthetic customer ETL helpers for standalone data generation."""

try:
    from ._routing import load_ds_attr
except ImportError:  # pragma: no cover - supports direct execution in DS container
    from _routing import load_ds_attr

assign_segments = load_ds_attr("synthetic.features", "assign_segments")
generate_observed_features = load_ds_attr(
    "synthetic.features",
    "generate_observed_features",
)
generate_latent_traits = load_ds_attr("synthetic.latents", "generate_latent_traits")

__all__ = [
    "assign_segments",
    "generate_latent_traits",
    "generate_observed_features",
]
