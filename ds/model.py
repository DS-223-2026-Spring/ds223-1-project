"""Simulation and bandit-scaffold helpers for standalone data generation."""

try:
    from .synthetic.simulate import (
        compute_conversion_probabilities,
        initialize_model_state,
        simulate_interactions,
    )
except ImportError:  # pragma: no cover - supports running inside the ds container
    from synthetic.simulate import (
        compute_conversion_probabilities,
        initialize_model_state,
        simulate_interactions,
    )

__all__ = [
    "compute_conversion_probabilities",
    "initialize_model_state",
    "simulate_interactions",
]
