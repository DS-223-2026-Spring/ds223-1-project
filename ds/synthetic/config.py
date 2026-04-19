"""Central configuration and calibration for synthetic retail data generation."""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class BetaPrior:
    """Beta prior parameters for one latent trait."""

    alpha: float
    beta: float


@dataclass(frozen=True, slots=True)
class LatentCalibration:
    """Latent trait priors."""

    price_sensitivity: BetaPrior = field(
        default_factory=lambda: BetaPrior(alpha=2.0, beta=5.0)
    )
    brand_loyalty: BetaPrior = field(
        default_factory=lambda: BetaPrior(alpha=3.0, beta=3.0)
    )
    impulse_tendency: BetaPrior = field(
        default_factory=lambda: BetaPrior(alpha=2.0, beta=4.0)
    )


@dataclass(frozen=True, slots=True)
class FeatureCalibration:
    """Observed feature-generation calibration."""

    frequency_base: float = 1.10
    frequency_loyalty_weight: float = 8.40
    frequency_impulse_weight: float = 1.50
    frequency_price_relief_weight: float = 0.90
    frequency_min: int = 1
    frequency_max: int = 18

    recency_base: float = 15.0
    recency_loyalty_curve_weight: float = 125.0
    recency_price_weight: float = 34.0
    recency_impulse_weight: float = 10.0
    recency_gamma_shape: float = 2.0
    recency_min: float = 1.0
    recency_max: float = 240.0

    avg_order_base: float = 46.0
    avg_order_impulse_weight: float = 33.0
    avg_order_loyalty_weight: float = 22.0
    avg_order_price_weight: float = 15.0
    avg_order_noise: float = 8.0
    avg_order_min: float = 15.0
    avg_order_max: float = 120.0

    basket_diversity_base: float = 1.35
    basket_diversity_impulse_weight: float = 4.10
    basket_diversity_loyalty_weight: float = 1.00
    basket_diversity_noise: float = 0.75
    basket_diversity_min: float = 1.0
    basket_diversity_max: float = 8.0

    regularity_base: float = 0.18
    regularity_loyalty_weight: float = 0.68
    regularity_impulse_weight: float = 0.10
    regularity_noise: float = 0.08
    regularity_min: float = 0.02
    regularity_max: float = 0.99

    monetary_multiplier_base: float = 0.78
    monetary_multiplier_loyalty_weight: float = 0.14
    monetary_multiplier_impulse_weight: float = 0.08
    monetary_multiplier_price_weight: float = 0.10
    monetary_multiplier_noise: float = 0.10
    monetary_multiplier_min: float = 0.55
    monetary_multiplier_max: float = 1.25
    monetary_min: float = 20.0
    monetary_max: float = 2200.0


@dataclass(frozen=True, slots=True)
class SegmentCalibration:
    """Observed-feature segment rules."""

    champion_recency_max: int = 30
    champion_frequency_min: int = 8
    champion_monetary_min: float = 400.0

    loyal_recency_max: int = 60
    loyal_frequency_min: int = 4

    at_risk_recency_min: int = 90
    at_risk_frequency_min: int = 3


@dataclass(frozen=True, slots=True)
class ActionCalibration:
    """One action's economics and response calibration."""

    action_id: int
    action_name: str
    description: str
    base_cost: float
    non_conversion_cost: float
    converted_cost_floor: float
    converted_cost_rate: float
    conversion_intercept: float
    conversion_price_weight: float
    conversion_loyalty_weight: float
    conversion_impulse_weight: float
    conversion_planner_weight: float
    revenue_base_multiplier: float
    revenue_price_weight: float
    revenue_loyalty_weight: float
    revenue_impulse_weight: float
    revenue_planner_weight: float
    revenue_basket_weight: float
    revenue_noise: float
    max_revenue: float


@dataclass(frozen=True, slots=True)
class SimulationCalibration:
    """Round sampling and interaction simulation calibration."""

    sampling_frequency_offset: float = 1.0
    seasonality_amplitude: float = 0.08
    seasonality_period: float = 52.0
    basket_noise_mean: float = 1.0
    basket_noise_sd: float = 0.10
    basket_noise_min: float = 0.75
    basket_noise_max: float = 1.35
    p_convert_min: float = 0.02
    p_convert_max: float = 0.90


@dataclass(frozen=True, slots=True)
class TargetMoments:
    """Calibration targets used to judge whether defaults remain plausible."""

    segment_mix: dict[str, float] = field(
        default_factory=lambda: {
            "Champion": 0.12,
            "Loyal": 0.40,
            "At-Risk": 0.18,
            "Lost": 0.30,
        }
    )
    segment_mix_tolerance: float = 0.05

    mean_avg_order_size: float = 65.0
    mean_avg_order_tolerance: float = 4.0

    conversion_rate_by_action: dict[str, float] = field(
        default_factory=lambda: {
            "no_action": 0.29,
            "discount_10": 0.18,
            "free_shipping": 0.20,
            "product_recommendation": 0.30,
            "bundle_offer": 0.28,
        }
    )
    conversion_tolerance: float = 0.06

    converted_revenue_range_by_action: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "no_action": (60.0, 78.0),
            "discount_10": (65.0, 85.0),
            "free_shipping": (62.0, 82.0),
            "product_recommendation": (70.0, 92.0),
            "bundle_offer": (92.0, 125.0),
        }
    )


@dataclass(frozen=True, slots=True)
class MonotonicityCalibration:
    """Expected directional relationships in the synthetic environment."""

    quantile_cutoff: float = 0.25
    loyalty_recency_gap_min: float = 25.0
    loyalty_frequency_gap_min: float = 2.5
    loyalty_monetary_gap_min: float = 130.0
    loyalty_regularity_gap_min: float = 0.18
    impulse_basket_gap_min: float = 1.20
    impulse_avg_order_gap_min: float = 10.0
    low_price_minus_high_price_aov_gap_min: float = 6.0
    bundle_minus_no_action_converted_revenue_gap_min: float = 18.0


@dataclass(frozen=True, slots=True)
class GeneratorCalibration:
    """All numeric generator calibration constants live here."""

    latents: LatentCalibration = field(default_factory=LatentCalibration)
    features: FeatureCalibration = field(default_factory=FeatureCalibration)
    segments: SegmentCalibration = field(default_factory=SegmentCalibration)
    simulation: SimulationCalibration = field(default_factory=SimulationCalibration)
    targets: TargetMoments = field(default_factory=TargetMoments)
    monotonicity: MonotonicityCalibration = field(
        default_factory=MonotonicityCalibration
    )
    actions: tuple[ActionCalibration, ...] = field(
        default_factory=lambda: (
            ActionCalibration(
                action_id=0,
                action_name="no_action",
                description="Control group; rely on organic conversion from loyal customers.",
                base_cost=0.00,
                non_conversion_cost=0.00,
                converted_cost_floor=0.00,
                converted_cost_rate=0.00,
                conversion_intercept=-2.55,
                conversion_price_weight=-0.30,
                conversion_loyalty_weight=3.00,
                conversion_impulse_weight=0.00,
                conversion_planner_weight=0.00,
                revenue_base_multiplier=1.00,
                revenue_price_weight=0.00,
                revenue_loyalty_weight=0.04,
                revenue_impulse_weight=0.00,
                revenue_planner_weight=0.00,
                revenue_basket_weight=0.00,
                revenue_noise=0.10,
                max_revenue=150.0,
            ),
            ActionCalibration(
                action_id=1,
                action_name="discount_10",
                description="10% discount for price-sensitive customers; margin-reducing but effective.",
                base_cost=6.50,
                non_conversion_cost=0.10,
                converted_cost_floor=6.50,
                converted_cost_rate=0.10,
                conversion_intercept=-1.80,
                conversion_price_weight=3.50,
                conversion_loyalty_weight=-1.60,
                conversion_impulse_weight=0.30,
                conversion_planner_weight=0.00,
                revenue_base_multiplier=1.08,
                revenue_price_weight=0.08,
                revenue_loyalty_weight=0.00,
                revenue_impulse_weight=0.00,
                revenue_planner_weight=0.00,
                revenue_basket_weight=0.00,
                revenue_noise=0.13,
                max_revenue=160.0,
            ),
            ActionCalibration(
                action_id=2,
                action_name="free_shipping",
                description="Shipping-friction relief for planning-oriented shoppers.",
                base_cost=4.99,
                non_conversion_cost=0.10,
                converted_cost_floor=4.99,
                converted_cost_rate=0.00,
                conversion_intercept=-1.75,
                conversion_price_weight=2.60,
                conversion_loyalty_weight=0.30,
                conversion_impulse_weight=-1.40,
                conversion_planner_weight=0.00,
                revenue_base_multiplier=1.03,
                revenue_price_weight=0.05,
                revenue_loyalty_weight=0.00,
                revenue_impulse_weight=0.00,
                revenue_planner_weight=0.03,
                revenue_basket_weight=0.00,
                revenue_noise=0.12,
                max_revenue=152.0,
            ),
            ActionCalibration(
                action_id=3,
                action_name="product_recommendation",
                description="Low-cost personalization that works best for loyal engaged shoppers.",
                base_cost=0.30,
                non_conversion_cost=0.30,
                converted_cost_floor=0.30,
                converted_cost_rate=0.00,
                conversion_intercept=-2.60,
                conversion_price_weight=0.00,
                conversion_loyalty_weight=2.20,
                conversion_impulse_weight=1.60,
                conversion_planner_weight=0.00,
                revenue_base_multiplier=1.10,
                revenue_price_weight=0.00,
                revenue_loyalty_weight=0.07,
                revenue_impulse_weight=0.06,
                revenue_planner_weight=0.00,
                revenue_basket_weight=0.00,
                revenue_noise=0.10,
                max_revenue=165.0,
            ),
            ActionCalibration(
                action_id=4,
                action_name="bundle_offer",
                description="Higher-basket bundle promotion for impulse-prone customers.",
                base_cost=9.00,
                non_conversion_cost=0.20,
                converted_cost_floor=9.00,
                converted_cost_rate=0.00,
                conversion_intercept=-2.55,
                conversion_price_weight=0.40,
                conversion_loyalty_weight=1.00,
                conversion_impulse_weight=2.50,
                conversion_planner_weight=0.00,
                revenue_base_multiplier=1.38,
                revenue_price_weight=0.00,
                revenue_loyalty_weight=0.05,
                revenue_impulse_weight=0.18,
                revenue_planner_weight=0.00,
                revenue_basket_weight=0.04,
                revenue_noise=0.16,
                max_revenue=220.0,
            ),
        )
    )


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
    calibration: GeneratorCalibration = field(default_factory=GeneratorCalibration)

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
