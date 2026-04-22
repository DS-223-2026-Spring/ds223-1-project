"""Shared backend metadata and field definitions."""

from __future__ import annotations

SERVICE_NAME = "back"

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
        "paths": ("/decide", "/feedback"),
        "methods": ("POST",),
        "owner_notes": (
            "Interaction logging is exposed through decision and feedback endpoints "
            "rather than raw table CRUD so the API matches the bandit workflow."
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
    "The `decide` endpoint is a placeholder integration point: the caller supplies `action_id` and optional scoring context until the DS-owned LinUCB selector is wired in.",
    "Context vectors are stored in `interactions.context_vector` as UTF-8 encoded JSON bytes so the API can exercise the BYTEA column without introducing a separate model serializer.",
    "Creating a simulation writes a record to the database only; orchestration-triggered execution remains a follow-up integration.",
)

PENDING_DEPENDENCIES = (
    "PM confirmation that the public resource names remain `customers`, `actions`, `simulations`, and `interactions`.",
    "DS integration for automatic action selection and model-state updates behind `/decide`.",
    "Orchestration wiring that turns `/simulations` POST requests into Prefect flow runs.",
)

API_TAGS = [
    {"name": "system", "description": "Health checks and API metadata."},
    {
        "name": "customers",
        "description": "Dummy CRUD endpoints backed by the customers and customer_latents tables.",
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
        "description": "Placeholder decision and feedback endpoints that write to the interactions table.",
    },
    {
        "name": "metrics",
        "description": "Read-only aggregated metrics derived from logged interactions.",
    },
]
