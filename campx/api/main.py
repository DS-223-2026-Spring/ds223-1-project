"""FastAPI backend service for the campaign optimization project."""

from __future__ import annotations
from pathlib import Path
import pandas as pd

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from .SQLHandler import SQLHandler
    from .crud import (
        ConflictError,
        complete_simulation_record,
        create_simulation_record,
        delete_customer_record,
        get_customer_detail_record,
        get_ds_artifact,
        get_metrics_snapshot,
        get_model_state_snapshot,
        get_simulation_record,
        import_ds_artifact_bundle,
        list_ds_artifacts,
        list_actions,
        list_customers,
        list_simulations,
        log_scored_decision,
        run_simulation_background,
        run_simulation_step,
        score_customer_actions,
        submit_feedback,
        upsert_customer_record,
    )
    from .database import get_db
    from .metadata import (
        API_ASSUMPTIONS,
        API_TAGS,
        PENDING_DEPENDENCIES,
        RESOURCE_NAMES,
        RESOURCE_STRUCTURE,
        SERVICE_NAME,
    )
    from .schemas import (
        ActionsResponse,
        ApiError,
        ApiStructureResource,
        ApiStructureResponse,
        AssumptionsResponse,
        CustomerCreate,
        CustomerDetailResponse,
        CustomerListItem,
        CustomerResponse,
        CustomerUpdate,
        DecisionScoreResponse,
        DecideResponse,
        DeleteResponse,
        DSArtifactBundleImportRequest,
        DSArtifactImportResponse,
        DSArtifactListResponse,
        DSArtifactResponse,
        FeedbackRequest,
        FeedbackResponse,
        HealthResponse,
        MetricsResponse,
        ModelStateResponse,
        SimulationCreate,
        SimulationResponse,
        SimulationStepResponse,
    )
except ImportError:
    from SQLHandler import SQLHandler
    from crud import (
        ConflictError,
        complete_simulation_record,
        create_simulation_record,
        delete_customer_record,
        get_customer_detail_record,
        get_ds_artifact,
        get_metrics_snapshot,
        get_model_state_snapshot,
        get_simulation_record,
        import_ds_artifact_bundle,
        list_ds_artifacts,
        list_actions,
        list_customers,
        list_simulations,
        log_scored_decision,
        run_simulation_background,
        run_simulation_step,
        score_customer_actions,
        submit_feedback,
        upsert_customer_record,
    )
    from database import get_db
    from metadata import (
        API_ASSUMPTIONS,
        API_TAGS,
        PENDING_DEPENDENCIES,
        RESOURCE_NAMES,
        RESOURCE_STRUCTURE,
        SERVICE_NAME,
    )
    from schemas import (
        ActionsResponse,
        ApiError,
        ApiStructureResource,
        ApiStructureResponse,
        AssumptionsResponse,
        CustomerCreate,
        CustomerDetailResponse,
        CustomerListItem,
        CustomerResponse,
        CustomerUpdate,
        DecisionScoreResponse,
        DecideResponse,
        DeleteResponse,
        DSArtifactBundleImportRequest,
        DSArtifactImportResponse,
        DSArtifactListResponse,
        DSArtifactResponse,
        FeedbackRequest,
        FeedbackResponse,
        HealthResponse,
        MetricsResponse,
        ModelStateResponse,
        SimulationCreate,
        SimulationResponse,
        SimulationStepResponse,
    )


def build_description() -> str:
    assumptions = "\n".join(f"- {item}" for item in API_ASSUMPTIONS)
    pending = "\n".join(f"- {item}" for item in PENDING_DEPENDENCIES)

    return (
        "FastAPI backend for the campaign optimization project.\n\n"
        "Implemented scope:\n"
        "- `backend` service/container\n"
        "- flat FastAPI package layout under `backend/`\n"
        "- CRUD endpoints for `customers`\n"
        "- simulation, decision, and metrics endpoints wired through the DB helper layer\n"
        "- DS artifact import and retrieval endpoints backed by PostgreSQL\n"
        "- Swagger/OpenAPI output at `/docs` and `/openapi.json`\n\n"
        "API assumptions:\n"
        f"{assumptions}\n\n"
        "Pending dependencies:\n"
        f"{pending}"
    )


def _error_slug(status_code: int) -> str:
    return {
        400: "bad_request",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        500: "internal_error",
        503: "service_unavailable",
    }.get(status_code, "internal_error")


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ApiError(
            error=_error_slug(status_code),
            message=message,
            code=status_code,
        ).model_dump(),
    )


app = FastAPI(
    title="Campaign Optimization Engine Backend",
    description=build_description(),
    version="0.4.0",
    openapi_tags=API_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_response(exc.status_code, detail)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(422, str(exc))


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return _error_response(500, str(exc))


@app.get("/health", response_model=HealthResponse, tags=["system"], summary="Health check")
def health_check() -> HealthResponse:
    """Confirm that the FastAPI service is running."""

    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get(
    "/assumptions",
    response_model=AssumptionsResponse,
    tags=["system"],
    summary="Document API assumptions and pending dependencies",
)
def get_assumptions() -> AssumptionsResponse:
    """Expose the current backend contract notes used during milestone work."""

    return AssumptionsResponse(
        resource_names=list(RESOURCE_NAMES),
        api_assumptions=list(API_ASSUMPTIONS),
        pending_dependencies=list(PENDING_DEPENDENCIES),
    )


@app.get(
    "/api-structure",
    response_model=ApiStructureResponse,
    tags=["system"],
    summary="Show agreed resource names and API structure",
)
def get_api_structure() -> ApiStructureResponse:
    """Return a machine-readable summary of the API surface."""

    return ApiStructureResponse(
        service=SERVICE_NAME,
        resources=[
            ApiStructureResource(
                resource=item["resource"],
                table=item["table"],
                paths=list(item["paths"]),
                methods=list(item["methods"]),
                owner_notes=item["owner_notes"],
            )
            for item in RESOURCE_STRUCTURE
        ],
    )


@app.get(
    "/customers",
    response_model=list[CustomerListItem],
    tags=["customers"],
    summary="List customers",
)
def get_customers(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: SQLHandler = Depends(get_db),
) -> list[CustomerListItem]:
    """Return customer RFM profiles as a raw array for frontend filtering."""

    items = list_customers(db, limit=limit, offset=offset)
    return [
        CustomerListItem(
            customer_id=item["customer_id"],
            segment_label=item["segment_label"],
            gender=item["gender"],
            recency=item["recency"],
            frequency=item["frequency"],
            monetary=item["monetary"],
            basket_diversity=item["basket_diversity"],
            avg_order_size=item["avg_order_size"],
            purchase_regularity=item["purchase_regularity"],
        )
        for item in items
    ]


@app.get(
    "/customers/{customer_id}",
    response_model=CustomerDetailResponse,
    response_model_exclude_none=True,
    tags=["customers"],
    summary="Fetch a single customer with interaction history",
)
def get_customer(
    customer_id: int,
    debug: bool = Query(default=False),
    db: SQLHandler = Depends(get_db),
) -> CustomerDetailResponse:
    """Return one customer profile, interaction history, and optional debug latents."""

    customer = get_customer_detail_record(db, customer_id, debug=debug)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} was not found.")
    return CustomerDetailResponse(**customer)


@app.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["customers"],
    summary="Create a customer",
)
def create_customer(
    payload: CustomerCreate,
    db: SQLHandler = Depends(get_db),
) -> CustomerResponse:
    """Create a customer row and optional latent debug values."""

    customer = upsert_customer_record(db, payload)
    return CustomerResponse(**customer)


@app.put(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    tags=["customers"],
    summary="Update a customer",
)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: SQLHandler = Depends(get_db),
) -> CustomerResponse:
    """Update mutable customer fields and latent debug values."""

    customer = upsert_customer_record(db, payload, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} was not found.")
    return CustomerResponse(**customer)


@app.delete(
    "/customers/{customer_id}",
    response_model=DeleteResponse,
    tags=["customers"],
    summary="Delete a customer",
)
def delete_customer(customer_id: int, db: SQLHandler = Depends(get_db)) -> DeleteResponse:
    """Delete one customer row and any cascading dependent records."""

    deleted = delete_customer_record(db, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} was not found.")
    return DeleteResponse(deleted=True, resource_id=customer_id)


@app.get(
    "/actions",
    response_model=ActionsResponse,
    tags=["actions"],
    summary="List seeded action definitions",
)
def get_actions(db: SQLHandler = Depends(get_db)) -> ActionsResponse:
    """Return the static promotion/action catalog from the database."""

    items = list_actions(db)
    return ActionsResponse(items=items, count=len(items))


@app.get(
    "/simulations",
    response_model=list[SimulationResponse],
    tags=["simulations"],
    summary="List simulation records",
)
def get_simulations(db: SQLHandler = Depends(get_db)) -> list[SimulationResponse]:
    """Return simulation summaries as a raw array ordered from newest to oldest."""

    return [SimulationResponse(**item) for item in list_simulations(db)]


@app.get(
    "/simulations/{simulation_id}",
    response_model=SimulationResponse,
    tags=["simulations"],
    summary="Fetch one simulation record",
)
def get_simulation(
    simulation_id: int,
    db: SQLHandler = Depends(get_db),
) -> SimulationResponse:
    """Return one simulation summary including status and cumulative reward."""

    simulation = get_simulation_record(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} was not found.")
    return SimulationResponse(**simulation)


@app.post(
    "/simulations",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["simulations"],
    summary="Create and launch a simulation",
)
def create_simulation(
    payload: SimulationCreate,
    background_tasks: BackgroundTasks,
    autostart: bool = Query(
        default=True,
        description="When false, create the simulation at t=0 without launching the background run.",
    ),
    db: SQLHandler = Depends(get_db),
) -> SimulationResponse:
    """Create a simulation record and enqueue the in-process simulation runner."""

    try:
        simulation = create_simulation_record(db, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if autostart:
        background_tasks.add_task(run_simulation_background, int(simulation["simulation_id"]))
    return SimulationResponse(**simulation)


@app.post(
    "/simulations/{simulation_id}/step",
    response_model=SimulationStepResponse,
    tags=["simulations"],
    summary="Run one LinUCB simulation round",
)
def step_simulation(
    simulation_id: int,
    db: SQLHandler = Depends(get_db),
) -> SimulationStepResponse:
    """Run one t -> t+1 LinUCB decision, outcome, and model update."""

    try:
        step = run_simulation_step(db, simulation_id)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if step is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} was not found.")
    return SimulationStepResponse(**step)


@app.put(
    "/simulations/{simulation_id}/complete",
    response_model=SimulationResponse,
    tags=["simulations"],
    summary="Mark a simulation as completed",
)
def complete_simulation(
    simulation_id: int,
    db: SQLHandler = Depends(get_db),
) -> SimulationResponse:
    """Mark a simulation record as completed in the database."""

    simulation = complete_simulation_record(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} was not found.")
    return SimulationResponse(**simulation)


@app.post(
    "/ds/artifacts",
    response_model=DSArtifactImportResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ds-artifacts"],
    summary="Import generated DS data-file payloads into the database",
)
def import_ds_artifacts(
    payload: DSArtifactBundleImportRequest,
    db: SQLHandler = Depends(get_db),
) -> DSArtifactImportResponse:
    """Persist generated customers, interactions, model state, and file payloads."""

    try:
        result = import_ds_artifact_bundle(db, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DSArtifactImportResponse(**result)


@app.get(
    "/ds/artifacts/{simulation_id}",
    response_model=DSArtifactListResponse,
    tags=["ds-artifacts"],
    summary="List generated DS artifacts stored for a simulation",
)
def list_simulation_ds_artifacts(
    simulation_id: int,
    db: SQLHandler = Depends(get_db),
) -> DSArtifactListResponse:
    """Return stored generated artifact names for one simulation."""

    artifacts = list_ds_artifacts(db, simulation_id)
    if artifacts is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} was not found.")
    return DSArtifactListResponse(
        simulation_id=simulation_id,
        items=artifacts,
        count=len(artifacts),
    )


@app.get(
    "/ds/artifacts/{simulation_id}/{artifact_name:path}",
    response_model=DSArtifactResponse,
    response_model_exclude_none=True,
    tags=["ds-artifacts"],
    summary="Fetch one generated DS artifact payload",
)
def get_simulation_ds_artifact(
    simulation_id: int,
    artifact_name: str,
    db: SQLHandler = Depends(get_db),
) -> DSArtifactResponse:
    """Return one generated artifact payload, such as customers.csv as JSON rows."""

    artifact = get_ds_artifact(db, simulation_id, artifact_name)
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Artifact {artifact_name!r} for simulation {simulation_id} "
                "was not found."
            ),
        )
    return DSArtifactResponse(**artifact)


@app.get(
    "/model/state",
    response_model=ModelStateResponse,
    tags=["interactions"],
    summary="Inspect the current LinUCB model state",
)
def get_model_state(
    simulation_id: int = Query(..., ge=1),
    db: SQLHandler = Depends(get_db),
) -> ModelStateResponse:
    """Return theta weights, pull counts, and update metadata for one simulation."""

    state = get_model_state_snapshot(db, simulation_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} was not found.")
    return ModelStateResponse(**state)


@app.post(
    "/decide",
    response_model=list[DecisionScoreResponse] | DecideResponse,
    tags=["interactions"],
    summary="Score actions for a customer and optionally log the chosen decision",
)
def decide(
    simulation_id: int = Query(..., ge=1),
    customer_id: int = Query(..., ge=1),
    preview: bool = Query(default=False),
    round_number: int | None = Query(default=None, ge=1),
    db: SQLHandler = Depends(get_db),
) -> list[DecisionScoreResponse] | DecideResponse:
    """Preview UCB scores or persist the highest-scoring action for one customer."""

    if preview:
        scores = score_customer_actions(db, simulation_id, customer_id)
        if scores is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Decision preview could not be computed because the referenced "
                    "simulation or customer record does not exist."
                ),
            )
        return [DecisionScoreResponse(**score) for score in scores]

    decision = log_scored_decision(
        db,
        simulation_id,
        customer_id,
        round_number=round_number,
    )
    if decision is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Decision could not be logged because the referenced simulation "
                "or customer record does not exist."
            ),
        )
    return DecideResponse(**decision)


@app.post(
    "/feedback",
    response_model=FeedbackResponse,
    tags=["interactions"],
    summary="Record interaction feedback",
)
def feedback(payload: FeedbackRequest, db: SQLHandler = Depends(get_db)) -> FeedbackResponse:
    """Close one interaction after its conversion window and update model state."""

    try:
        response = submit_feedback(db, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(
            status_code=404,
            detail=f"Interaction {payload.interaction_id} was not found.",
        )
    return FeedbackResponse(**response)


@app.get(
    "/metrics",
    response_model=MetricsResponse,
    tags=["metrics"],
    summary="Read interaction metrics for a simulation",
)
def get_metrics(
    simulation_id: int = Query(..., ge=1),
    sample_rate: int = Query(default=1, ge=1, le=1000),
    db: SQLHandler = Depends(get_db),
) -> MetricsResponse:
    """Return dashboard metrics, recent interactions, and policy comparison series."""

    metrics = get_metrics_snapshot(db, simulation_id, sample_rate=sample_rate)
    if metrics is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} was not found.")
    return MetricsResponse(**metrics)



@app.get(
    "/baselines",
    tags=["baselines"],
    summary="Get random policy baseline cumulative reward",
)
def get_baselines():
    """Return the cumulative reward array for the random uniform baseline."""

    candidate_paths = [
        Path("/app/baselines/policy_round_traces.csv"),
        Path("/app/outputs/baselines/policy_round_traces.csv"),
        Path("/app/outputs/synthetic_data/baselines/policy_round_traces.csv"),
        Path("baselines/policy_round_traces.csv"),
    ]

    csv_path = next((p for p in candidate_paths if p.exists()), None)

    if csv_path is None:
        return {
            "random_baseline_rewards": [],
            "available": False,
            "message": "Baseline file not found in backend container.",
        }

    df = pd.read_csv(csv_path)

    if "policy_name" not in df.columns or "round_number" not in df.columns or "cumulative_reward" not in df.columns:
        raise HTTPException(
            status_code=500,
            detail="Baseline CSV is missing required columns.",
        )

    random_df = (
        df[df["policy_name"] == "random_uniform"]
        .sort_values("round_number")
    )

    return {
        "random_baseline_rewards": random_df["cumulative_reward"].tolist(),
        "available": True,
        "source": str(csv_path),
    }