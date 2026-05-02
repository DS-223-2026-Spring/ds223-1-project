"""Simulation helpers, LinUCB policy, and simple baseline benchmarking."""

try:
    from ._routing import load_ds_attr
except ImportError:  # pragma: no cover - supports direct execution in DS container
    from _routing import load_ds_attr

run_baseline_comparison = load_ds_attr("baselines", "run_baseline_comparison")
LinUCBPolicy = load_ds_attr("linucb", "LinUCBPolicy")
LinUCBScore = load_ds_attr("linucb", "LinUCBScore")
compute_conversion_probabilities = load_ds_attr(
    "synthetic.simulate",
    "compute_conversion_probabilities",
)
initialize_model_state = load_ds_attr("synthetic.simulate", "initialize_model_state")
simulate_interactions = load_ds_attr("synthetic.simulate", "simulate_interactions")

__all__ = [
    "compute_conversion_probabilities",
    "initialize_model_state",
    "LinUCBPolicy",
    "LinUCBScore",
    "run_baseline_comparison",
    "simulate_interactions",
]
