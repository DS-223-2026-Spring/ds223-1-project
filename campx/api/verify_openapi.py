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

try:
    import main as app_module
    from database import get_db
    from main import app
    from metadata import SERVICE_NAME
except ImportError:
    from . import main as app_module
    from .database import get_db
    from .main import app
    from .metadata import SERVICE_NAME


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
    "num_rounds": 100,
    "num_customers": 50,
    "alpha": 0.5,
    "context_dim": 6,
    "conversion_window_hours": 48,
    "notes": "Local verification record",
    "started_at": FIXED_TIME,
    "completed_at": FIXED_TIME,
    "status": "completed",
    "cumulative_reward": 12.5,
    "rounds_completed": 4,
}

SAMPLE_DECISION_SCORES = [
    {
        "action": "discount_10",
        "exploit": 2.1,
        "explore": 0.9,
        "ucb_score": 3.0,
        "cost": 6.5,
    },
    {
        "action": "product_recommendation",
        "exploit": 1.8,
        "explore": 0.7,
        "ucb_score": 2.5,
        "cost": 0.3,
    },
]

SAMPLE_DECISION = {
    "interaction_id": 1,
    "recommended_action": "discount_10",
    "scores": SAMPLE_DECISION_SCORES,
}

SAMPLE_FEEDBACK = {
    "interaction_id": 1,
    "reward": 12.5,
    "observed_at": FIXED_TIME,
    "model_updated": True,
}

SAMPLE_METRICS = {
    "simulation_id": 1,
    "status": "completed",
    "rounds_completed": 4,
    "cumulative_reward": 12.5,
    "avg_reward_per_round": 3.125,
    "pending_observations": 1,
    "cumulative_reward_series": [
        {"round": 1, "cumulative_reward": 5.0},
        {"round": 2, "cumulative_reward": 12.5},
    ],
    "action_distribution": [
        {"round": 1, "action": "discount_10"},
        {"round": 2, "action": "product_recommendation"},
    ],
    "conversion_by_action": [
        {"action": "discount_10", "conversion_rate": 0.5, "n_pulls": 2},
        {"action": "product_recommendation", "conversion_rate": None, "n_pulls": 1},
    ],
    "recent_interactions": [
        {
            "interaction_id": 1,
            "customer_id": 1,
            "action_id": 1,
            "simulation_id": 1,
            "round_number": 2,
            "converted": True,
            "revenue": 15.0,
            "cost": 2.5,
            "reward": 12.5,
            "decision_at": FIXED_TIME,
            "observed_at": FIXED_TIME,
            "action": "discount_10",
        },
    ],
    "total_interactions": 4,
    "conversions": 2,
    "total_revenue": 21.5,
    "total_cost": 9.0,
    "total_reward": 12.5,
}

SAMPLE_MODEL_STATE = {
    "simulation_id": 1,
    "alpha": 0.5,
    "round_number": 4,
    "updated_at": FIXED_TIME,
    "n_pulls": {
        "no_action": 1,
        "discount_10": 2,
        "free_shipping": 0,
        "product_recommendation": 1,
        "bundle_offer": 0,
    },
    "theta": {
        "recency": {
            "no_action": 0.0,
            "discount_10": 0.1,
            "free_shipping": 0.0,
            "product_recommendation": 0.2,
            "bundle_offer": 0.0,
        },
        "frequency": {
            "no_action": 0.0,
            "discount_10": 0.1,
            "free_shipping": 0.0,
            "product_recommendation": 0.2,
            "bundle_offer": 0.0,
        },
        "monetary": {
            "no_action": 0.0,
            "discount_10": 0.1,
            "free_shipping": 0.0,
            "product_recommendation": 0.2,
            "bundle_offer": 0.0,
        },
        "basket_diversity": {
            "no_action": 0.0,
            "discount_10": 0.1,
            "free_shipping": 0.0,
            "product_recommendation": 0.2,
            "bundle_offer": 0.0,
        },
        "avg_order_size": {
            "no_action": 0.0,
            "discount_10": 0.1,
            "free_shipping": 0.0,
            "product_recommendation": 0.2,
            "bundle_offer": 0.0,
        },
        "purchase_regularity": {
            "no_action": 0.0,
            "discount_10": 0.1,
            "free_shipping": 0.0,
            "product_recommendation": 0.2,
            "bundle_offer": 0.0,
        },
    },
}

SAMPLE_DS_IMPORT = {
    "simulation_id": 1,
    "sim_name": "Local Verify",
    "customers_inserted": 1,
    "actions_upserted": 1,
    "interactions_inserted": 1,
    "model_state_rows_upserted": 1,
    "artifacts_stored": 5,
    "completed": True,
}

SAMPLE_DS_ARTIFACT = {
    "artifact_id": 1,
    "simulation_id": 1,
    "artifact_name": "customers.csv",
    "artifact_type": "records",
    "content_type": "application/json",
    "payload_json": [SAMPLE_CUSTOMER],
    "payload_text": None,
    "created_at": FIXED_TIME,
}

SAMPLE_NESTED_DS_ARTIFACT = {
    "artifact_id": 2,
    "simulation_id": 1,
    "artifact_name": "eda/segment_counts.png",
    "artifact_type": "base64",
    "content_type": "image/png",
    "payload_json": None,
    "payload_text": "iVBORw0KGgo=",
    "created_at": FIXED_TIME,
}


def _registered_api_paths() -> dict[str, set[str]]:
    paths: dict[str, set[str]] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = {method.lower() for method in route.methods or set()}
        methods -= {"head", "options"}
        if methods:
            openapi_path = route.path.replace("{artifact_name:path}", "{artifact_name}")
            paths.setdefault(openapi_path, set()).update(methods)
    return paths


def _install_endpoint_stubs() -> dict[str, object]:
    originals: dict[str, object] = {}

    def list_customers_stub(db, limit=100, offset=0):
        return [dict(SAMPLE_CUSTOMER)]

    def get_customer_detail_record_stub(db, customer_id, debug=False):
        if customer_id != 1:
            return None
        record = {
            "customer_id": 1,
            "segment_label": "Champion",
            "gender": "F",
            "rfm": {
                "recency": 10.0,
                "frequency": 4.0,
                "monetary": 120.5,
                "basket_diversity": 3.0,
                "avg_order_size": 30.125,
                "purchase_regularity": 0.8,
            },
            "interactions": [
                {
                    "interaction_id": 1,
                    "simulation_id": 1,
                    "action": "discount_10",
                    "converted": True,
                    "revenue": 15.0,
                    "reward": 12.5,
                    "decision_at": FIXED_TIME,
                    "observed_at": FIXED_TIME,
                }
            ],
        }
        if debug:
            record["latents"] = {
                "z_price_sensitivity": 0.2,
                "z_brand_loyalty": 0.7,
                "z_impulse_tendency": 0.4,
            }
        return record

    def upsert_customer_record_stub(db, payload, customer_id=None):
        if customer_id not in (None, 1):
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

    def score_customer_actions_stub(db, simulation_id, customer_id):
        if simulation_id != 1 or customer_id != 1:
            return None
        return [dict(item) for item in SAMPLE_DECISION_SCORES]

    def log_scored_decision_stub(db, simulation_id, customer_id, round_number=None):
        if simulation_id != 1 or customer_id != 1:
            return None
        return dict(SAMPLE_DECISION)

    def submit_feedback_stub(db, payload):
        if payload.interaction_id != 1:
            return None
        return dict(SAMPLE_FEEDBACK, interaction_id=payload.interaction_id)

    def get_model_state_snapshot_stub(db, simulation_id):
        if simulation_id != 1:
            return None
        return dict(SAMPLE_MODEL_STATE)

    def get_metrics_snapshot_stub(db, simulation_id):
        if simulation_id != 1:
            return None
        return dict(SAMPLE_METRICS)

    def import_ds_artifact_bundle_stub(db, payload):
        record = dict(SAMPLE_DS_IMPORT)
        record["sim_name"] = payload.simulation.sim_name
        return record

    def list_ds_artifacts_stub(db, simulation_id):
        if simulation_id != 1:
            return None
        items = []
        for sample in (SAMPLE_DS_ARTIFACT, SAMPLE_NESTED_DS_ARTIFACT):
            item = dict(sample)
            item.pop("payload_json")
            item.pop("payload_text")
            items.append(item)
        return items

    def get_ds_artifact_stub(db, simulation_id, artifact_name):
        if simulation_id != 1:
            return None
        if artifact_name == "customers.csv":
            return dict(SAMPLE_DS_ARTIFACT)
        if artifact_name == "eda/segment_counts.png":
            return dict(SAMPLE_NESTED_DS_ARTIFACT)
        return None

    replacements = {
        "list_customers": list_customers_stub,
        "get_customer_detail_record": get_customer_detail_record_stub,
        "upsert_customer_record": upsert_customer_record_stub,
        "delete_customer_record": delete_customer_record_stub,
        "list_actions": list_actions_stub,
        "list_simulations": list_simulations_stub,
        "create_simulation_record": create_simulation_record_stub,
        "complete_simulation_record": complete_simulation_record_stub,
        "score_customer_actions": score_customer_actions_stub,
        "log_scored_decision": log_scored_decision_stub,
        "submit_feedback": submit_feedback_stub,
        "get_model_state_snapshot": get_model_state_snapshot_stub,
        "get_metrics_snapshot": get_metrics_snapshot_stub,
        "import_ds_artifact_bundle": import_ds_artifact_bundle_stub,
        "list_ds_artifacts": list_ds_artifacts_stub,
        "get_ds_artifact": get_ds_artifact_stub,
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
                    "num_rounds": 100,
                    "num_customers": 50,
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
            "POST /ds/artifacts",
            client.post(
                "/ds/artifacts",
                json={
                    "simulation": {
                        "sim_name": "Local Verify",
                        "num_rounds": 100,
                        "num_customers": 50,
                        "alpha": 0.5,
                        "context_dim": 6,
                        "conversion_window_hours": 48,
                        "notes": "verification import",
                    },
                    "customers": [
                        {
                            "customer_id": 1,
                            "gender": "F",
                            "segment": "Champion",
                            "recency": 9.5,
                            "frequency": 3.0,
                            "monetary": 100.0,
                            "basket_diversity": 2.5,
                            "avg_order_size": 25.0,
                            "purchase_regularity": 0.7,
                        }
                    ],
                    "customer_latents": [
                        {
                            "customer_id": 1,
                            "z_price_sensitivity": 0.1,
                            "z_brand_loyalty": 0.8,
                            "z_impulse_tendency": 0.3,
                        }
                    ],
                    "actions": [
                        {
                            "action_id": 1,
                            "action_name": "discount_10",
                            "action_cost": 6.5,
                            "target_latent": "price_sensitivity",
                            "description": "verification action",
                        }
                    ],
                    "interactions": [
                        {
                            "round_number": 1,
                            "customer_id": 1,
                            "action_id": 1,
                            "converted": True,
                            "revenue": 15.0,
                            "cost": 6.5,
                            "ucb_score": 0.4,
                        }
                    ],
                    "model_state": [
                        {
                            "action_id": 1,
                            "round_number": 0,
                            "n_pulls": 1,
                            "theta_json": "[0, 0, 0, 0, 0, 0]",
                            "a_json": (
                                "[[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], "
                                "[0, 0, 1, 0, 0, 0], [0, 0, 0, 1, 0, 0], "
                                "[0, 0, 0, 0, 1, 0], [0, 0, 0, 0, 0, 1]]"
                            ),
                            "b_json": "[0, 0, 0, 0, 0, 0]",
                            "alpha": 0.5,
                        }
                    ],
                },
            ),
            201,
        ),
        ("GET /ds/artifacts/1", client.get("/ds/artifacts/1"), 200),
        (
            "GET /ds/artifacts/1/customers.csv",
            client.get("/ds/artifacts/1/customers.csv"),
            200,
        ),
        (
            "GET /ds/artifacts/1/eda/segment_counts.png",
            client.get("/ds/artifacts/1/eda/segment_counts.png"),
            200,
        ),
        ("GET /model/state", client.get("/model/state?simulation_id=1"), 200),
        (
            "POST /decide preview",
            client.post("/decide?simulation_id=1&customer_id=1&preview=true"),
            200,
        ),
        (
            "POST /decide live",
            client.post("/decide?simulation_id=1&customer_id=1"),
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
    if client.get("/ds/artifacts/999").status_code != 404:
        print("GET /ds/artifacts/999 did not return 404")
        return False
    if client.get("/ds/artifacts/1/missing.csv").status_code != 404:
        print("GET /ds/artifacts/1/missing.csv did not return 404")
        return False
    if client.get("/model/state?simulation_id=999").status_code != 404:
        print("GET /model/state?simulation_id=999 did not return 404")
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
