"""Simulation helpers and simple baseline model benchmarking."""

try:
    from .baselines import run_baseline_comparison
    from .synthetic.simulate import (
        compute_conversion_probabilities,
        initialize_model_state,
        simulate_interactions,
    )
except ImportError:  # pragma: no cover - supports running inside the ds container
    from baselines import run_baseline_comparison
    from synthetic.simulate import (
        compute_conversion_probabilities,
        initialize_model_state,
        simulate_interactions,
    )

__all__ = [
    "compute_conversion_probabilities",
    "initialize_model_state",
    "run_baseline_comparison",
    "simulate_interactions",
]
