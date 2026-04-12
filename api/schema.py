"""Pydantic schemas for request and response validation."""
from pydantic import BaseModel

class CustomerContext(BaseModel):
    recency: float
    frequency: float
    monetary: float
    basket_diversity: float
    avg_order_size: float
    purchase_regularity: float

class DecisionResponse(BaseModel):
    customer_id: int
    action_id: int
    action_name: str
    predicted_reward: float

class FeedbackRequest(BaseModel):
    interaction_id: int
    converted: bool
    revenue: float

class MetricsResponse(BaseModel):
    cumulative_reward: float
    avg_reward_per_step: float
    total_rounds: int
    action_distribution: dict
