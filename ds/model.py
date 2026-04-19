"""Simulation and bandit-scaffold helpers for standalone data generation."""

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
