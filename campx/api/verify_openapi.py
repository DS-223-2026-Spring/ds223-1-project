"""Backend-local script for verifying endpoint wiring and OpenAPI generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.main as app_module
from app.database import get_db
from app.main import app
from app.metadata import SERVICE_NAME


SYSTEM_PATHS = ("/health", "/assumptions", "/api-structure")
FIXED_TIME = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)

SAMPLE_CUSTOMER = {
    "customer_id": 1,
    "gender": "F",
    "segment_label": "Champion",
    "recency": 10.0,
    "frequency": 4.0,
    "monetary": 120.5,
    "basket_diversity": 3.0,
    "avg_order_size": 30.125,
    "purchase_regularity": 0.8,
    "created_at": FIXED_TIME,
    "latents": {
        "customer_id": 1,
        "z_price_sensitivity": 0.2,
        "z_brand_loyalty": 0.7,
        "z_impulse_tendency": 0.4,
    },
}

SAMPLE_ACTION = {
    "action_id": 1,
    "action_name": "Discount",
    "action_cost": 2.5,
    "target_latent": "z_price_sensitivity",
    "description": "Placeholder seeded action",
}

SAMPLE_SIMULATION = {
    "simulation_id": 1,
    "sim_name": "Milestone 2 Verification",
    "num_rounds": 10,
    "num_customers": 5,
    "alpha": 0.5,
    "context_dim": 6,
    "conversion_window_hours": 48,
    "notes": "Local verification record",
    "started_at": FIXED_TIME,
    "completed_at": FIXED_TIME,
}

SAMPLE_DECISION = {
    "interaction_id": 1,
    "recommended_action_id": 1,
    "placeholder": True,
    "stored_context_encoding": "json-bytes",
    "note": "Local verification path",
}

SAMPLE_FEEDBACK = {
    "interaction_id": 1,
    "converted": True,
    "revenue": 15.0,
    "reward": 12.5,
    "observed_at": FIXED_TIME,
}

SAMPLE_METRICS = {
    "simulation_id": 1,
    "total_interactions": 4,
    "conversions": 2,
    "total_revenue": 21.5,
    "total_cost": 9.0,
    "total_reward": 12.5,
}


def _registered_api_paths() -> dict[str, set[str]]:
    paths: dict[str, set[str]] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = {method.lower() for method in route.methods or set()}
        methods -= {"head", "options"}
        if methods:
            paths.setdefault(route.path, set()).update(methods)
    return paths


def _install_endpoint_stubs() -> dict[str, object]:
    originals: dict[str, object] = {}

    def list_customers_stub(db, limit=100, offset=0):
        return [dict(SAMPLE_CUSTOMER)]

    def get_customer_record_stub(db, customer_id):
        if customer_id != 1:
            return None
        return dict(SAMPLE_CUSTOMER)

    def create_customer_record_stub(db, payload):
        record = dict(SAMPLE_CUSTOMER)
        record.update(payload.model_dump(exclude_none=True, exclude_unset=True))
        if payload.latents is not None:
            record["latents"] = {"customer_id": 1, **payload.latents.model_dump()}
        return record

    def update_customer_record_stub(db, customer_id, payload):
        if customer_id != 1:
            return None
        record = dict(SAMPLE_CUSTOMER)
        record.update(payload.model_dump(exclude_none=True, exclude_unset=True))
        if payload.latents is not None:
            record["latents"] = {"customer_id": 1, **payload.latents.model_dump()}
        return record

    def delete_customer_record_stub(db, customer_id):
        return customer_id == 1

    def list_actions_stub(db):
        return [dict(SAMPLE_ACTION)]

    def list_simulations_stub(db):
        return [dict(SAMPLE_SIMULATION)]

    def create_simulation_record_stub(db, payload):
        record = dict(SAMPLE_SIMULATION)
        record.update(payload.model_dump(exclude_none=True, exclude_unset=True))
        record["simulation_id"] = 1
        return record

    def complete_simulation_record_stub(db, simulation_id):
        if simulation_id != 1:
            return None
        return dict(SAMPLE_SIMULATION)

    def log_decision_stub(db, payload):
        if payload.customer_id != 1 or payload.simulation_id != 1:
            return None
        return dict(SAMPLE_DECISION, recommended_action_id=payload.action_id or 1)

    def submit_feedback_stub(db, payload):
        if payload.interaction_id != 1:
            return None
        return dict(SAMPLE_FEEDBACK, interaction_id=payload.interaction_id)

    def get_metrics_snapshot_stub(db, simulation_id):
        if simulation_id != 1:
            return None
        return dict(SAMPLE_METRICS)

    replacements = {
        "list_customers": list_customers_stub,
        "get_customer_record": get_customer_record_stub,
        "create_customer_record": create_customer_record_stub,
        "update_customer_record": update_customer_record_stub,
        "delete_customer_record": delete_customer_record_stub,
        "list_actions": list_actions_stub,
        "list_simulations": list_simulations_stub,
        "create_simulation_record": create_simulation_record_stub,
        "complete_simulation_record": complete_simulation_record_stub,
        "log_decision": log_decision_stub,
        "submit_feedback": submit_feedback_stub,
        "get_metrics_snapshot": get_metrics_snapshot_stub,
    }

    for name, replacement in replacements.items():
        originals[name] = getattr(app_module, name)
        setattr(app_module, name, replacement)

    app.dependency_overrides[get_db] = lambda: object()
    return originals


def _remove_endpoint_stubs(originals: dict[str, object]) -> None:
    for name, original in originals.items():
        setattr(app_module, name, original)
    app.dependency_overrides.pop(get_db, None)


def _check_response(response, expected_status, label):
    if response.status_code != expected_status:
        print(f"{label} failed with status {response.status_code}")
        print(response.text)
        return False
    return True


def _verify_endpoints(client: TestClient) -> bool:
    requests = [
        ("GET /health", client.get("/health"), 200),
        ("GET /assumptions", client.get("/assumptions"), 200),
        ("GET /api-structure", client.get("/api-structure"), 200),
        ("GET /customers", client.get("/customers?limit=5&offset=0"), 200),
        ("GET /customers/1", client.get("/customers/1"), 200),
        (
            "POST /customers",
            client.post(
                "/customers",
                json={
                    "gender": "F",
                    "segment_label": "Champion",
                    "recency": 9.5,
                    "frequency": 3.0,
                    "monetary": 100.0,
                    "basket_diversity": 2.5,
                    "avg_order_size": 25.0,
                    "purchase_regularity": 0.7,
                    "latents": {
                        "z_price_sensitivity": 0.1,
                        "z_brand_loyalty": 0.8,
                        "z_impulse_tendency": 0.3,
                    },
                },
            ),
            201,
        ),
        (
            "PUT /customers/1",
            client.put(
                "/customers/1",
                json={
                    "segment_label": "Loyal",
                    "latents": {
                        "z_price_sensitivity": 0.2,
                        "z_brand_loyalty": 0.9,
                        "z_impulse_tendency": 0.2,
                    },
                },
            ),
            200,
        ),
        ("DELETE /customers/1", client.delete("/customers/1"), 200),
        ("GET /actions", client.get("/actions"), 200),
        ("GET /simulations", client.get("/simulations"), 200),
        (
            "POST /simulations",
            client.post(
                "/simulations",
                json={
                    "sim_name": "Local Verify",
                    "num_rounds": 10,
                    "num_customers": 5,
                    "alpha": 0.5,
                    "context_dim": 6,
                    "conversion_window_hours": 48,
                    "notes": "verification",
                },
            ),
            201,
        ),
        ("PUT /simulations/1/complete", client.put("/simulations/1/complete"), 200),
        (
            "POST /decide",
            client.post(
                "/decide",
                json={
                    "simulation_id": 1,
                    "customer_id": 1,
                    "action_id": 1,
                    "round_number": 1,
                    "context_vector": [0.1, 0.2, 0.3],
                    "ucb_score": 0.9,
                    "cost": 1.5,
                },
            ),
            200,
        ),
        (
            "POST /feedback",
            client.post(
                "/feedback",
                json={
                    "interaction_id": 1,
                    "converted": True,
                    "revenue": 15.0,
                },
            ),
            200,
        ),
        ("GET /metrics", client.get("/metrics?simulation_id=1"), 200),
    ]

    for label, response, expected_status in requests:
        if not _check_response(response, expected_status, label):
            return False

    if client.get("/customers/999").status_code != 404:
        print("GET /customers/999 did not return 404")
        return False
    if client.put("/simulations/999/complete").status_code != 404:
        print("PUT /simulations/999/complete did not return 404")
        return False
    if client.get("/metrics?simulation_id=999").status_code != 404:
        print("GET /metrics?simulation_id=999 did not return 404")
        return False

    return True


def main() -> int:
    originals = _install_endpoint_stubs()
    client = TestClient(app, raise_server_exceptions=False)

    try:
        if not _verify_endpoints(client):
            return 1

        docs_url = app.docs_url
        if docs_url is None:
            print("Swagger docs are disabled")
            return 1

        docs_response = client.get(docs_url)
        if docs_response.status_code != 200 or "Swagger UI" not in docs_response.text:
            print(f"{docs_url} did not render Swagger UI correctly")
            return 1

        openapi_url = app.openapi_url
        if openapi_url is None:
            print("OpenAPI output is disabled")
            return 1

        openapi_response = client.get(openapi_url)
        if openapi_response.status_code != 200:
            print(f"{openapi_url} failed with status {openapi_response.status_code}")
            return 1

        schema = openapi_response.json()
        expected_paths = _registered_api_paths()
        missing_paths = sorted(path for path in expected_paths if path not in schema["paths"])
        if missing_paths:
            print("Missing OpenAPI paths:")
            for path in missing_paths:
                print(f"- {path}")
            return 1

        missing_methods: list[str] = []
        for path, methods in expected_paths.items():
            documented_methods = set(schema["paths"][path])
            for method in sorted(methods - documented_methods):
                missing_methods.append(f"{method.upper()} {path}")

        if missing_methods:
            print("Missing OpenAPI operations:")
            for item in missing_methods:
                print(f"- {item}")
            return 1

        print("Endpoint and Swagger/OpenAPI verification OK")
        print(f"Service: {SERVICE_NAME}")
        print(f"Docs URL: {docs_url}")
        print(f"OpenAPI URL: {openapi_url}")
        print(f"Documented paths: {len(schema['paths'])}")
        for path in sorted(expected_paths):
            operations = ", ".join(method.upper() for method in sorted(expected_paths[path]))
            print(f"- {path}: {operations}")
        return 0
    finally:
        _remove_endpoint_stubs(originals)


if __name__ == "__main__":
    raise SystemExit(main())
