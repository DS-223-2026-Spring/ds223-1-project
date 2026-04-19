"""Configuration for standalone synthetic retail data generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FEATURE_COLUMNS = [
    "recency",
    "frequency",
    "monetary",
    "basket_diversity",
    "avg_order_size",
    "purchase_regularity",
]

LATENT_COLUMNS = [
    "z_price_sensitivity",
    "z_brand_loyalty",
    "z_impulse_tendency",
]

SUPPORTED_POLICY_MODES = {"random_policy", "bandit_scaffold"}


@dataclass(slots=True)
class SyntheticDataConfig:
    """Runtime configuration for synthetic dataset generation."""

    n_customers: int = 500
    n_rounds: int = 5000
    random_seed: int = 42
    output_dir: Path | str = Path("outputs/synthetic_data")
    simulation_id: str | None = None
    policy_mode: str = "random_policy"
    alpha: float = 0.5

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)

        if self.n_customers <= 0:
            raise ValueError("n_customers must be positive")
        if self.n_rounds <= 0:
            raise ValueError("n_rounds must be positive")
        if self.policy_mode not in SUPPORTED_POLICY_MODES:
            raise ValueError(
                f"policy_mode must be one of {sorted(SUPPORTED_POLICY_MODES)}"
            )
        if self.alpha <= 0:
            raise ValueError("alpha must be positive")

        if self.simulation_id is None:
            self.simulation_id = (
                f"synthetic_seed{self.random_seed}_"
                f"cust{self.n_customers}_rounds{self.n_rounds}"
            )
