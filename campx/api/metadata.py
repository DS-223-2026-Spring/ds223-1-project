"""Shared backend metadata and API contract notes."""

from __future__ import annotations

SERVICE_NAME = "backend"

RESOURCE_NAMES = (
    "customers",
    "actions",
    "simulations",
    "interactions",
    "metrics",
)

RESOURCE_STRUCTURE = (
    {
        "resource": "customers",
        "table": "customers",
        "paths": ("/customers", "/customers/{customer_id}"),
        "methods": ("GET", "POST", "PUT", "DELETE"),
        "owner_notes": (
            "Primary milestone-2 CRUD resource agreed with the DB schema because "
            "customers and customer_latents already support end-to-end reads and writes."
        ),
    },
    {
        "resource": "actions",
        "table": "actions",
        "paths": ("/actions",),
        "methods": ("GET",),
        "owner_notes": (
            "Read-only reference resource seeded by the DB initialization scripts and "
            "consumed by DS and backend decision flows."
        ),
    },
    {
        "resource": "simulations",
        "table": "simulations",
        "paths": ("/simulations", "/simulations/{simulation_id}/complete"),
        "methods": ("GET", "POST", "PUT"),
        "owner_notes": (
            "Simulation records provide the shared coordination point between backend, "
            "DB persistence, and later orchestration-triggered runs."
        ),
    },
    {
        "resource": "interactions",
        "table": "interactions",
        "paths": ("/decide", "/feedback", "/model/state"),
        "methods": ("GET", "POST"),
        "owner_notes": (
            "Decision scoring, feedback submission, and model inspection are exposed "
            "through workflow-specific endpoints rather than raw table CRUD."
        ),
    },
    {
        "resource": "metrics",
        "table": "interactions",
        "paths": ("/metrics",),
        "methods": ("GET",),
        "owner_notes": (
            "Metrics are derived from interactions and surfaced as read-only aggregates "
            "for PM review and experiment monitoring."
        ),
    },
)

CUSTOMER_FIELDS = (
    "gender",
    "segment_label",
    "recency",
    "frequency",
    "monetary",
    "basket_diversity",
    "avg_order_size",
    "purchase_regularity",
)

LATENT_FIELDS = (
    "z_price_sensitivity",
    "z_brand_loyalty",
    "z_impulse_tendency",
)

API_ASSUMPTIONS = (
    "The `customers` resource is the primary milestone-2 CRUD surface because the schema and helper layer already support it end to end.",
    "Public resource names are `customers`, `actions`, `simulations`, `interactions`, and `metrics`, matching the shared API structure exposed by the backend.",
    "The backend reuses DB-facing helper logic copied from `etl/` into the backend container so imports work without changing the ETL codebase.",
    "Simulation creation is exposed through `POST /simulations` as the single public write route for simulation records.",
    "The `decide` endpoint now computes LinUCB-style exploit and explore scores from database-backed model state reconstructed from observed interactions.",
    "Context vectors are stored in `interactions.context_vector` as float64 binary feature arrays so feedback updates can reproduce the learning state.",
    "The frontend should reach the service at `http://backend:8000` inside docker-compose.",
)

PENDING_DEPENDENCIES = (
    "Full metrics payload expansion is still required before the Interaction and Analytics pages can fully replace mock data.",
    "Orchestration wiring that turns simulation creation into Prefect flow runs rather than a database-only placeholder write.",
)

API_TAGS = [
    {"name": "system", "description": "Health checks and API metadata."},
    {
        "name": "customers",
        "description": "CRUD endpoints backed by the customers and customer_latents tables.",
    },
    {
        "name": "actions",
        "description": "Reference actions seeded from the database init scripts.",
    },
    {
        "name": "simulations",
        "description": "Simulation records used to coordinate experimentation runs.",
    },
    {
        "name": "interactions",
        "description": "Decision and feedback endpoints that write to the interactions table.",
    },
    {
        "name": "metrics",
        "description": "Read-only aggregated metrics derived from logged interactions.",
    },
]
