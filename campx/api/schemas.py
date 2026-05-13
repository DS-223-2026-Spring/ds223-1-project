"""Pydantic request and response schemas for the backend API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


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


class CustomerListItem(BaseModel):
    customer_id: int
    segment_label: str
    gender: str
    recency: float
    frequency: float
    monetary: float
    basket_diversity: float
    avg_order_size: float
    purchase_regularity: float


class CustomerRfmResponse(BaseModel):
    recency: float
    frequency: float
    monetary: float
    basket_diversity: float
    avg_order_size: float
    purchase_regularity: float


class CustomerInteractionResponse(BaseModel):
    interaction_id: int
    simulation_id: int
    action: str
    converted: bool | None = None
    revenue: float | None = None
    reward: float | None = None
    decision_at: datetime
    observed_at: datetime | None = None


class CustomerDetailResponse(BaseModel):
    customer_id: int
    segment_label: str
    gender: str
    rfm: CustomerRfmResponse
    interactions: list[CustomerInteractionResponse]
    latents: CustomerLatentsPayload | None = None


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
    num_rounds: int = Field(..., ge=100, le=50000)
    num_customers: int = Field(..., ge=50, le=10000)
    alpha: float = Field(default=0.5, ge=0.0, le=2.0)
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


class SimulationStepResponse(BaseModel):
    simulation_id: int
    round_number: int
    interaction_id: int
    customer_id: int
    action_id: int
    action: str
    converted: bool
    revenue: float
    cost: float
    reward: float
    p_convert: float
    exploit: float
    explore: float
    ucb_score: float
    warm_start: bool = False
    selection_reason: Literal["warm_start", "ucb"] = "ucb"
    model_updated: bool
    completed: bool


class SimulationsResponse(BaseModel):
    items: list[SimulationResponse]
    count: int


class DecisionScoreResponse(BaseModel):
    action: str
    exploit: float
    explore: float
    ucb_score: float
    cost: float


class DecideResponse(BaseModel):
    interaction_id: int
    recommended_action: str
    scores: list[DecisionScoreResponse]


class FeedbackRequest(BaseModel):
    interaction_id: int = Field(..., gt=0)
    converted: bool
    revenue: float = Field(default=0.0, ge=0.0)
    converted_at: datetime | None = None
    observed_at: datetime | None = None


class FeedbackResponse(BaseModel):
    interaction_id: int
    reward: float
    observed_at: datetime
    model_updated: bool


class PolicyCumulativeRewardPoint(BaseModel):
    model_config = ConfigDict(extra="allow")

    round: int


class ActionDistributionPoint(BaseModel):
    round: int
    action: str


class ConversionByActionItem(BaseModel):
    action: str
    conversion_rate: float | None = None
    n_pulls: int


class SegmentPerformanceItem(BaseModel):
    segment_label: str
    action_label: str
    pulls: int
    conversions: int
    avg_reward: float | None = None


class RecentInteractionItem(BaseModel):
    interaction_id: int
    customer_id: int
    action_id: int
    simulation_id: int
    round_number: int
    converted: bool | None = None
    revenue: float | None = None
    cost: float | None = None
    reward: float | None = None
    decision_at: datetime
    observed_at: datetime | None = None
    action: str


class MetricsResponse(BaseModel):
    simulation_id: int
    status: Literal["running", "completed"]
    rounds_completed: int
    cumulative_reward: float | None = None
    avg_reward_per_round: float | None = None
    pending_observations: int
    cumulative_reward_series: list[PolicyCumulativeRewardPoint]
    action_distribution: list[ActionDistributionPoint]
    conversion_by_action: list[ConversionByActionItem]
    segment_performance: list[SegmentPerformanceItem]
    recent_interactions: list[RecentInteractionItem]
    total_interactions: int
    conversions: int
    total_revenue: float
    total_cost: float
    total_reward: float | None = None


class ModelStateResponse(BaseModel):
    simulation_id: int
    alpha: float
    round_number: int
    updated_at: datetime | None = None
    n_pulls: dict[str, int]
    theta: dict[str, dict[str, float]]


class DSArtifactPayload(BaseModel):
    artifact_name: str = Field(..., min_length=1, max_length=150)
    artifact_type: str = Field(default="json", max_length=30)
    content_type: str = Field(default="application/json", max_length=100)
    payload_json: Any | None = None
    payload_text: str | None = None

    @model_validator(mode="after")
    def validate_payload_present(self) -> "DSArtifactPayload":
        if self.payload_json is None and self.payload_text is None:
            raise ValueError("Either payload_json or payload_text must be provided.")
        return self


class DSGeneratedRowBase(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class DSGeneratedCustomerRow(DSGeneratedRowBase):
    customer_id: int = Field(..., ge=1)
    gender: Literal["M", "F"]
    segment_label: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("segment_label", "segment"),
    )
    recency: float
    frequency: float
    monetary: float
    basket_diversity: float
    avg_order_size: float
    purchase_regularity: float


class DSGeneratedCustomerLatentRow(DSGeneratedRowBase):
    customer_id: int = Field(..., ge=1)
    z_price_sensitivity: float
    z_brand_loyalty: float
    z_impulse_tendency: float


class DSGeneratedActionRow(DSGeneratedRowBase):
    action_id: int = Field(..., ge=0)
    action_name: str = Field(..., min_length=1)
    action_cost: float = Field(
        ...,
        validation_alias=AliasChoices("action_cost", "base_cost"),
    )
    target_latent: str | None = Field(default=None, min_length=1)
    description: str | None = None


class DSGeneratedInteractionRow(DSGeneratedRowBase):
    round_number: int = Field(..., ge=1)
    customer_id: int = Field(..., ge=1)
    action_id: int = Field(..., ge=0)
    converted: bool | None = None
    revenue: float | None = Field(default=None, ge=0.0)
    cost: float | None = Field(default=None, ge=0.0)
    ucb_score: float | None = None
    converted_at: datetime | None = None
    observed_at: datetime | None = None
    context_vector: Any | None = Field(
        default=None,
        validation_alias=AliasChoices("context_vector", "context", "raw_context"),
    )


class DSGeneratedModelStateRow(DSGeneratedRowBase):
    action_id: int = Field(..., ge=0)
    round_number: int = Field(default=0, ge=0)
    n_pulls: int = Field(default=0, ge=0)
    theta_json: Any = Field(
        ...,
        validation_alias=AliasChoices("theta_json", "theta_vector", "theta"),
    )
    a_json: Any = Field(
        ...,
        validation_alias=AliasChoices("a_json", "a_matrix"),
    )
    b_json: Any = Field(
        ...,
        validation_alias=AliasChoices("b_json", "b_vector"),
    )
    alpha: float = Field(..., ge=0.0)


class DSArtifactBundleImportRequest(BaseModel):
    simulation: SimulationCreate
    customers: list[DSGeneratedCustomerRow] = Field(default_factory=list)
    customer_latents: list[DSGeneratedCustomerLatentRow] = Field(default_factory=list)
    actions: list[DSGeneratedActionRow] = Field(default_factory=list)
    interactions: list[DSGeneratedInteractionRow] = Field(default_factory=list)
    model_state: list[DSGeneratedModelStateRow] = Field(default_factory=list)
    artifacts: list[DSArtifactPayload] = Field(default_factory=list)
    complete_simulation: bool = True


class DSArtifactImportResponse(BaseModel):
    simulation_id: int
    sim_name: str
    customers_inserted: int
    actions_upserted: int
    interactions_inserted: int
    model_state_rows_upserted: int
    artifacts_stored: int
    completed: bool


class DSArtifactListItem(BaseModel):
    artifact_id: int
    simulation_id: int
    artifact_name: str
    artifact_type: str
    content_type: str
    created_at: datetime | None = None


class DSArtifactListResponse(BaseModel):
    simulation_id: int
    items: list[DSArtifactListItem]
    count: int


class DSArtifactResponse(DSArtifactListItem):
    payload_json: Any | None = None
    payload_text: str | None = None


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
