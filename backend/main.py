"""FastAPI backend service for milestone-2 backend tasks."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from crud import (
    complete_simulation_record,
    create_customer_record,
    create_simulation_record,
    delete_customer_record,
    get_customer_record,
    get_metrics_snapshot,
    list_actions,
    list_customers,
    list_simulations,
    log_decision,
    submit_feedback,
    update_customer_record,
)
from database import get_db
from models import (
    API_ASSUMPTIONS,
    RESOURCE_STRUCTURE,
    API_TAGS,
    PENDING_DEPENDENCIES,
    RESOURCE_NAMES,
    SERVICE_NAME,
)
from schema import (
    ActionsResponse,
    AssumptionsResponse,
    ApiStructureResource,
    ApiStructureResponse,
    CustomerCreate,
    CustomerResponse,
    CustomersResponse,
    CustomerUpdate,
    DecideRequest,
    DecideResponse,
    DeleteResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    MetricsResponse,
    SimulationCreate,
    SimulationResponse,
    SimulationsResponse,
)
from SQLHandler import SQLHandler


def build_description() -> str:
    assumptions = "\n".join(f"- {item}" for item in API_ASSUMPTIONS)
    pending = "\n".join(f"- {item}" for item in PENDING_DEPENDENCIES)

    return (
        "FastAPI backend for the campaign optimization project.\n\n"
        "Implemented milestone-2 scope:\n"
        "- `back` backend service/container\n"
        "- dummy CRUD endpoints for `customers`\n"
        "- placeholder request/response schemas for customer, simulation, and interaction flows\n"
        "- Swagger/OpenAPI output at `/docs` and `/openapi.json`\n\n"
        "API assumptions:\n"
        f"{assumptions}\n\n"
        "Pending dependencies:\n"
        f"{pending}"
    )


app = FastAPI(
    title="Campaign Optimization Engine Backend",
    description=build_description(),
    version="0.2.0",
    openapi_tags=API_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["system"], summary="Health check")
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get(
    "/assumptions",
    response_model=AssumptionsResponse,
    tags=["system"],
    summary="Document API assumptions and pending dependencies",
)
def get_assumptions() -> AssumptionsResponse:
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
    response_model=CustomersResponse,
    tags=["customers"],
    summary="List customers",
)
def get_customers(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: SQLHandler = Depends(get_db),
) -> CustomersResponse:
    items = list_customers(db, limit=limit, offset=offset)
    return CustomersResponse(items=items, count=len(items))


@app.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    tags=["customers"],
    summary="Fetch a single customer",
)
def get_customer(customer_id: int, db: SQLHandler = Depends(get_db)) -> CustomerResponse:
    customer = get_customer_record(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} was not found.")
    return CustomerResponse(**customer)


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
    customer = create_customer_record(db, payload)
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
    customer = update_customer_record(db, customer_id, payload)
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
    items = list_actions(db)
    return ActionsResponse(items=items, count=len(items))


@app.get(
    "/simulations",
    response_model=SimulationsResponse,
    tags=["simulations"],
    summary="List simulation records",
)
def get_simulations(db: SQLHandler = Depends(get_db)) -> SimulationsResponse:
    items = list_simulations(db)
    return SimulationsResponse(items=items, count=len(items))


@app.post(
    "/simulations",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["simulations"],
    summary="Create a simulation record",
)
def create_simulation(
    payload: SimulationCreate,
    db: SQLHandler = Depends(get_db),
) -> SimulationResponse:
    simulation = create_simulation_record(db, payload)
    return SimulationResponse(**simulation)


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
    simulation = complete_simulation_record(db, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} was not found.")
    return SimulationResponse(**simulation)


@app.post(
    "/decide",
    response_model=DecideResponse,
    tags=["interactions"],
    summary="Log a placeholder action decision",
)
def decide(payload: DecideRequest, db: SQLHandler = Depends(get_db)) -> DecideResponse:
    decision = log_decision(db, payload)
    if decision is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Decision could not be logged because the referenced simulation, "
                "customer, or action record does not exist."
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
    response = submit_feedback(db, payload)
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
    db: SQLHandler = Depends(get_db),
) -> MetricsResponse:
    metrics = get_metrics_snapshot(db, simulation_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} was not found.")
    return MetricsResponse(**metrics)
