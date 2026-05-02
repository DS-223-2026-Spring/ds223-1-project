"""Pydantic request and response schemas for the backend API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class ApiError(BaseModel):
    error: str
    message: str
    code: int


class CustomerLatentsPayload(BaseModel):
    z_price_sensitivity: float
    z_brand_loyalty: float
    z_impulse_tendency: float


class CustomerLatentsResponse(CustomerLatentsPayload):
    customer_id: int


class CustomerCreate(BaseModel):
    gender: Literal["M", "F"]
    segment_label: Literal["Champion", "Loyal", "At-Risk", "Lost"]
    recency: float
    frequency: float
    monetary: float
    basket_diversity: float
    avg_order_size: float
    purchase_regularity: float
    latents: CustomerLatentsPayload | None = None


class CustomerUpdate(BaseModel):
    gender: Literal["M", "F"] | None = None
    segment_label: Literal["Champion", "Loyal", "At-Risk", "Lost"] | None = None
    recency: float | None = None
    frequency: float | None = None
    monetary: float | None = None
    basket_diversity: float | None = None
    avg_order_size: float | None = None
    purchase_regularity: float | None = None
    latents: CustomerLatentsPayload | None = None


class CustomerResponse(BaseModel):
    customer_id: int
    gender: str
    segment_label: str
    recency: float
    frequency: float
    monetary: float
    basket_diversity: float
    avg_order_size: float
    purchase_regularity: float
    created_at: datetime | None = None
    latents: CustomerLatentsResponse | None = None


class CustomersResponse(BaseModel):
    items: list[CustomerResponse]
    count: int


class DeleteResponse(BaseModel):
    deleted: bool
    resource_id: int


class ActionResponse(BaseModel):
    action_id: int
    action_name: str
    action_cost: float
    target_latent: str
    description: str


class ActionsResponse(BaseModel):
    items: list[ActionResponse]
    count: int


class SimulationCreate(BaseModel):
    sim_name: str = Field(..., min_length=1, max_length=100)
    num_rounds: int = Field(..., gt=0)
    num_customers: int = Field(..., gt=0)
    alpha: float = Field(default=0.5, ge=0.0)
    context_dim: int = Field(default=6, gt=0)
    conversion_window_hours: int = Field(default=48, gt=0)
    notes: str | None = Field(default=None, max_length=500)


class SimulationResponse(BaseModel):
    simulation_id: int
    sim_name: str
    num_rounds: int
    num_customers: int
    alpha: float
    context_dim: int
    conversion_window_hours: int
    notes: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str | None = None
    cumulative_reward: float | None = None
    rounds_completed: int = 0


class SimulationsResponse(BaseModel):
    items: list[SimulationResponse]
    count: int


class DecideRequest(BaseModel):
    simulation_id: int = Field(..., gt=0)
    customer_id: int = Field(..., gt=0)
    action_id: int = Field(..., gt=0)
    round_number: int = Field(default=1, gt=0)
    context_vector: list[float] = Field(default_factory=list)
    ucb_score: float = 0.0
    cost: float | None = Field(default=None, ge=0.0)


class DecideResponse(BaseModel):
    interaction_id: int
    recommended_action_id: int
    # placeholder: bool
    # stored_context_encoding: str
    # note: str


class FeedbackRequest(BaseModel):
    interaction_id: int = Field(..., gt=0)
    converted: bool
    revenue: float = Field(default=0.0, ge=0.0)
    converted_at: datetime | None = None
    observed_at: datetime | None = None


class FeedbackResponse(BaseModel):
    interaction_id: int
    converted: bool | None = None
    revenue: float
    reward: float | None = None
    observed_at: datetime | None = None


class MetricsResponse(BaseModel):
    simulation_id: int
    total_interactions: int
    conversions: int
    total_revenue: float
    total_cost: float
    total_reward: float


class AssumptionsResponse(BaseModel):
    resource_names: list[str]
    api_assumptions: list[str]
    pending_dependencies: list[str]


class ApiStructureResource(BaseModel):
    resource: str
    table: str
    paths: list[str]
    methods: list[str]
    owner_notes: str


class ApiStructureResponse(BaseModel):
    service: str
    resources: list[ApiStructureResource]
