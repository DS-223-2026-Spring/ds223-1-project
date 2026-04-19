"""Action definitions and marketing economics."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    """Metadata and economic defaults for one campaign action."""

    action_id: int
    action_name: str
    description: str
    base_cost: float
    send_cost: float
    revenue_multiplier: float
    revenue_noise: float
    max_revenue: float


def get_action_definitions() -> tuple[ActionDefinition, ...]:
    """Return the canonical standalone action set."""

    return (
        ActionDefinition(
            action_id=0,
            action_name="no_action",
            description="Control group; rely on organic conversion from loyal customers.",
            base_cost=0.00,
            send_cost=0.00,
            revenue_multiplier=1.00,
            revenue_noise=0.11,
            max_revenue=150.0,
        ),
        ActionDefinition(
            action_id=1,
            action_name="discount_10",
            description="10% discount for price-sensitive customers; margin-reducing but effective.",
            base_cost=6.50,
            send_cost=0.10,
            revenue_multiplier=1.08,
            revenue_noise=0.13,
            max_revenue=155.0,
        ),
        ActionDefinition(
            action_id=2,
            action_name="free_shipping",
            description="Shipping-friction relief for planning-oriented shoppers.",
            base_cost=4.99,
            send_cost=0.10,
            revenue_multiplier=1.03,
            revenue_noise=0.12,
            max_revenue=150.0,
        ),
        ActionDefinition(
            action_id=3,
            action_name="product_recommendation",
            description="Low-cost personalization that works best for loyal engaged shoppers.",
            base_cost=0.30,
            send_cost=0.30,
            revenue_multiplier=1.10,
            revenue_noise=0.10,
            max_revenue=160.0,
        ),
        ActionDefinition(
            action_id=4,
            action_name="bundle_offer",
            description="Higher-basket bundle promotion for impulse-prone customers.",
            base_cost=9.00,
            send_cost=0.20,
            revenue_multiplier=1.45,
            revenue_noise=0.16,
            max_revenue=220.0,
        ),
    )


def actions_to_frame(actions: tuple[ActionDefinition, ...]) -> pd.DataFrame:
    """Return export-ready action metadata."""

    return pd.DataFrame(
        [
            {
                "action_id": action.action_id,
                "action_name": action.action_name,
                "description": action.description,
                "base_cost": round(action.base_cost, 2),
            }
            for action in actions
        ]
    )
