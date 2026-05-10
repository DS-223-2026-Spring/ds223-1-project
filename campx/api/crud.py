"""Database-backed CRUD helpers for the FastAPI backend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

try:
    from .SQLHandler import SQLHandler
    from .db_interactions import (
        complete_simulation,
        create_simulation,
        get_customer_by_id,
        get_customer_latents,
        get_simulation_artifact as db_get_simulation_artifact,
        list_simulation_artifacts as db_list_simulation_artifacts,
        log_interaction as db_log_interaction,
        observe_outcome as db_observe_outcome,
        upsert_action as db_upsert_action,
        upsert_customer as db_upsert_customer,
        upsert_model_state,
        upsert_simulation_artifact as db_upsert_simulation_artifact,
    )
    from .schemas import (
        CustomerCreate,
        CustomerUpdate,
        DSArtifactBundleImportRequest,
        FeedbackRequest,
        SimulationCreate,
    )
except ImportError:
    from SQLHandler import SQLHandler
    from db_interactions import (
        complete_simulation,
        create_simulation,
        get_customer_by_id,
        get_customer_latents,
        get_simulation_artifact as db_get_simulation_artifact,
        list_simulation_artifacts as db_list_simulation_artifacts,
        log_interaction as db_log_interaction,
        observe_outcome as db_observe_outcome,
        upsert_action as db_upsert_action,
        upsert_customer as db_upsert_customer,
        upsert_model_state,
        upsert_simulation_artifact as db_upsert_simulation_artifact,
    )
    from schemas import (
        CustomerCreate,
        CustomerUpdate,
        DSArtifactBundleImportRequest,
        FeedbackRequest,
        SimulationCreate,
    )


MODEL_FEATURE_COLUMNS = (
    "recency",
    "frequency",
    "monetary",
    "basket_diversity",
    "avg_order_size",
    "purchase_regularity",
)

DEFAULT_ACTION_TARGET_LATENTS = {
    0: "brand_loyalty",
    1: "price_sensitivity",
    2: "price_sensitivity+planning",
    3: "brand_loyalty+impulse",
    4: "impulse_tendency",
}


class ConflictError(Exception):
    """Raised when a request conflicts with existing persisted state."""


def _dump_model(model: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True, exclude_unset=exclude_unset)
    return model.dict(exclude_none=True, exclude_unset=exclude_unset)


def _serialize_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, memoryview):
        return bytes(value).hex()
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _serialize_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {key: _serialize_value(value) for key, value in record.items()}


def _split_customer_row(row: dict[str, Any]) -> dict[str, Any]:
    row = _serialize_record(row) or {}
    latents = None

    if row.get("z_price_sensitivity") is not None:
        latents = {
            "customer_id": row["customer_id"],
            "z_price_sensitivity": row.pop("z_price_sensitivity"),
            "z_brand_loyalty": row.pop("z_brand_loyalty"),
            "z_impulse_tendency": row.pop("z_impulse_tendency"),
        }
    else:
        row.pop("z_price_sensitivity", None)
        row.pop("z_brand_loyalty", None)
        row.pop("z_impulse_tendency", None)

    row["latents"] = latents
    return row


def _select_one(db: SQLHandler, query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    df = db.select(query, params)
    if df.empty:
        return None
    return _serialize_record(df.iloc[0].to_dict())


def _fetchone_raw(db: SQLHandler, query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    db.cursor.execute(query, params)
    row = db.cursor.fetchone()
    if row is None:
        return None
    columns = [column.name for column in db.cursor.description]
    return dict(zip(columns, row, strict=True))


def _fetchall_raw(db: SQLHandler, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    db.cursor.execute(query, params)
    rows = db.cursor.fetchall()
    columns = [column.name for column in db.cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _action_exists(db: SQLHandler, action_id: int) -> bool:
    return _select_one(
        db,
        "SELECT action_id FROM public.actions WHERE action_id = %s",
        (action_id,),
    ) is not None


def _customer_exists(db: SQLHandler, customer_id: int) -> bool:
    return _select_one(
        db,
        "SELECT customer_id FROM public.customers WHERE customer_id = %s",
        (customer_id,),
    ) is not None


def _simulation_exists(db: SQLHandler, simulation_id: int) -> bool:
    return _select_one(
        db,
        "SELECT simulation_id FROM public.simulations WHERE simulation_id = %s",
        (simulation_id,),
    ) is not None


def _simulation_name_exists(db: SQLHandler, sim_name: str) -> bool:
    return _select_one(
        db,
        "SELECT simulation_id FROM public.simulations WHERE sim_name = %s",
        (sim_name,),
    ) is not None


def _normalize_context_dim(raw_value: Any) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = len(MODEL_FEATURE_COLUMNS)
    return min(max(value, 1), len(MODEL_FEATURE_COLUMNS))


def _array_to_bytes(values: np.ndarray) -> bytes:
    return np.asarray(values, dtype=np.float64).tobytes()


def _decode_context_vector(payload: Any, expected_size: int) -> np.ndarray:
    if payload is None:
        raise ValueError("Missing context vector payload")

    if isinstance(payload, memoryview):
        raw = bytes(payload)
    elif isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
    elif isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raise ValueError("Unsupported context vector payload type")

    binary_size = expected_size * np.dtype(np.float64).itemsize
    if len(raw) == binary_size:
        values = np.frombuffer(raw, dtype=np.float64).copy()
        if values.size == expected_size and np.isfinite(values).all():
            return values

    try:
        decoded = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Could not decode stored context vector") from exc

    values = np.asarray(decoded, dtype=float)
    if values.size != expected_size or not np.isfinite(values).all():
        raise ValueError("Stored context vector does not match expected dimension")
    return values


def _get_customer_feature_vector(db: SQLHandler, customer_id: int) -> np.ndarray | None:
    customer = _serialize_record(get_customer_by_id(db, customer_id))
    if customer is None:
        return None
    return np.asarray(
        [float(customer[column]) for column in MODEL_FEATURE_COLUMNS],
        dtype=np.float64,
    )


def get_customer_record(db: SQLHandler, customer_id: int) -> dict[str, Any] | None:
    customer = _serialize_record(get_customer_by_id(db, customer_id))
    if customer is None:
        return None

    latents = _serialize_record(get_customer_latents(db, customer_id))
    customer["latents"] = latents
    return customer


def get_customer_detail_record(
    db: SQLHandler,
    customer_id: int,
    *,
    debug: bool = False,
) -> dict[str, Any] | None:
    customer = _serialize_record(get_customer_by_id(db, customer_id))
    if customer is None:
        return None

    interactions_df = db.select(
        """
        SELECT
            i.interaction_id,
            i.simulation_id,
            a.action_name AS action,
            CASE
                WHEN i.observed_at IS NULL THEN NULL
                ELSE i.converted
            END AS converted,
            CASE
                WHEN i.observed_at IS NULL THEN NULL
                ELSE i.revenue
            END AS revenue,
            CASE
                WHEN i.observed_at IS NULL THEN NULL
                ELSE i.reward
            END AS reward,
            i.decision_at,
            i.observed_at
        FROM public.interactions AS i
        JOIN public.actions AS a
            ON a.action_id = i.action_id
        WHERE i.customer_id = %s
        ORDER BY i.decision_at DESC, i.interaction_id DESC
        """,
        (customer_id,),
    )

    detail = {
        "customer_id": int(customer["customer_id"]),
        "segment_label": customer["segment_label"],
        "gender": customer["gender"],
        "rfm": {
            "recency": float(customer["recency"]),
            "frequency": float(customer["frequency"]),
            "monetary": float(customer["monetary"]),
            "basket_diversity": float(customer["basket_diversity"]),
            "avg_order_size": float(customer["avg_order_size"]),
            "purchase_regularity": float(customer["purchase_regularity"]),
        },
        "interactions": [
            _serialize_record(row)
            for row in interactions_df.to_dict(orient="records")
        ],
    }

    if debug:
        latents = _serialize_record(get_customer_latents(db, customer_id))
        if latents is not None:
            latents.pop("customer_id", None)
            detail["latents"] = latents

    return detail


def list_customers(db: SQLHandler, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM public.view_customer_with_latents
        ORDER BY customer_id
        LIMIT %s OFFSET %s
    """
    df = db.select(query, (limit, offset))
    return [_split_customer_row(row) for row in df.to_dict(orient="records")]


def upsert_customer_record(
    db: SQLHandler,
    payload: CustomerCreate | CustomerUpdate,
    customer_id: int | None = None,
) -> dict[str, Any] | None:
    if customer_id is not None and not _customer_exists(db, customer_id):
        return None

    data = _dump_model(payload, exclude_unset=True)
    latents = data.pop("latents", {}) or {}

    result = _select_one(
        db,
        """
        SELECT sp_upsert_customer(
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        ) AS customer_id
        """,
        (
            customer_id,
            data.get("gender"),
            data.get("segment_label"),
            data.get("recency"),
            data.get("frequency"),
            data.get("monetary"),
            data.get("basket_diversity"),
            data.get("avg_order_size"),
            data.get("purchase_regularity"),
            latents.get("z_price_sensitivity"),
            latents.get("z_brand_loyalty"),
            latents.get("z_impulse_tendency"),
        ),
    )

    db.commit()
    return get_customer_record(db, result["customer_id"])


def delete_customer_record(db: SQLHandler, customer_id: int) -> bool:
    db.cursor.execute(
        "DELETE FROM public.customers WHERE customer_id = %s RETURNING customer_id",
        (customer_id,),
    )
    deleted = db.cursor.fetchone()
    db.commit()
    return deleted is not None


def list_actions(db: SQLHandler) -> list[dict[str, Any]]:
    df = db.select(
        """
        SELECT action_id, action_name, action_cost, target_latent, description
        FROM public.actions
        ORDER BY action_id
        """
    )
    return [_serialize_record(row) for row in df.to_dict(orient="records")]


def _get_simulation_record(db: SQLHandler, simulation_id: int) -> dict[str, Any] | None:
    return _select_one(
        db,
        """
        SELECT *
        FROM public.view_simulation_summary
        WHERE simulation_id = %s
        """,
        (simulation_id,),
    )


def list_simulations(db: SQLHandler) -> list[dict[str, Any]]:
    df = db.select(
        """
        SELECT *
        FROM public.view_simulation_summary
        ORDER BY simulation_id DESC
        """
    )
    return [_serialize_record(row) for row in df.to_dict(orient="records")]


def create_simulation_record(db: SQLHandler, payload: SimulationCreate) -> dict[str, Any]:
    data = _dump_model(payload)
    if _simulation_name_exists(db, data["sim_name"]):
        raise ConflictError(f"Simulation name '{data['sim_name']}' already exists.")
    simulation_id = create_simulation(db, **data)
    return _get_simulation_record(db, simulation_id)


def complete_simulation_record(db: SQLHandler, simulation_id: int) -> dict[str, Any] | None:
    if not _simulation_exists(db, simulation_id):
        return None
    complete_simulation(db, simulation_id)
    return _get_simulation_record(db, simulation_id)


def _row_value(
    row: dict[str, Any],
    *names: str,
    default: Any = None,
) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and not _is_missing_scalar(value):
            return value
    return default


def _is_missing_scalar(value: Any) -> bool:
    return isinstance(value, float) and np.isnan(value)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, datetime):
        return value.isoformat()
    if _is_missing_scalar(value):
        return None
    return value


def _records_json_ready(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_json_ready(row) for row in rows]


def _payload_to_float_array(payload: Any) -> np.ndarray:
    if payload is None:
        raise ValueError("Missing vector or matrix payload")
    if isinstance(payload, str):
        payload = json.loads(payload)
    return np.asarray(payload, dtype=np.float64)


def _payload_to_bytes(payload: Any) -> bytes:
    return _payload_to_float_array(payload).tobytes()


def _context_vector_from_payload(
    interaction: dict[str, Any],
    customer: dict[str, Any],
) -> bytes:
    context_payload = _row_value(
        interaction,
        "context_vector",
        "context",
        "raw_context",
    )
    if context_payload is not None:
        return _payload_to_bytes(context_payload)

    return _array_to_bytes(
        np.asarray(
            [float(customer[column]) for column in MODEL_FEATURE_COLUMNS],
            dtype=np.float64,
        )
    )


def _store_records_artifact(
    db: SQLHandler,
    simulation_id: int,
    artifact_name: str,
    rows: list[dict[str, Any]],
) -> int:
    if not rows:
        return 0
    db_upsert_simulation_artifact(
        db,
        simulation_id=simulation_id,
        artifact_name=artifact_name,
        artifact_type="records",
        content_type="application/json",
        payload_json=_records_json_ready(rows),
    )
    return 1


def import_ds_artifact_bundle(
    db: SQLHandler,
    payload: DSArtifactBundleImportRequest,
) -> dict[str, Any]:
    """Persist generated DS data-file payloads into relational and artifact tables."""

    data = _dump_model(payload)
    simulation_data = data["simulation"]
    sim_name = simulation_data["sim_name"]
    if _simulation_name_exists(db, sim_name):
        raise ConflictError(f"Simulation name '{sim_name}' already exists.")

    simulation_id = create_simulation(db, **simulation_data)
    customer_id_map: dict[int, int] = {}
    customers = data.get("customers") or []
    latents = data.get("customer_latents") or []
    actions = data.get("actions") or []
    interactions = data.get("interactions") or []
    model_state = data.get("model_state") or []
    artifacts = data.get("artifacts") or []

    latents_by_customer = {
        int(row["customer_id"]): row
        for row in latents
        if row.get("customer_id") is not None
    }
    customer_rows_by_source_id: dict[int, dict[str, Any]] = {}

    for row in customers:
        source_customer_id = int(row["customer_id"])
        latent_row = latents_by_customer.get(source_customer_id, {})
        db_customer_id = db_upsert_customer(
            db,
            customer_id=None,
            gender=_row_value(row, "gender", default="F"),
            segment_label=_row_value(row, "segment_label", "segment"),
            recency=_row_value(row, "recency"),
            frequency=_row_value(row, "frequency"),
            monetary=_row_value(row, "monetary"),
            basket_diversity=_row_value(row, "basket_diversity"),
            avg_order_size=_row_value(row, "avg_order_size"),
            purchase_regularity=_row_value(row, "purchase_regularity"),
            z_price_sensitivity=_row_value(latent_row, "z_price_sensitivity"),
            z_brand_loyalty=_row_value(latent_row, "z_brand_loyalty"),
            z_impulse_tendency=_row_value(latent_row, "z_impulse_tendency"),
        )
        customer_id_map[source_customer_id] = int(db_customer_id)
        customer_rows_by_source_id[source_customer_id] = row

    action_costs: dict[int, float] = {}
    for row in actions:
        action_id = int(row["action_id"])
        action_cost = float(_row_value(row, "action_cost", "base_cost", default=0.0))
        action_costs[action_id] = action_cost
        db_upsert_action(
            db,
            action_id=action_id,
            action_name=_row_value(row, "action_name", default=f"action_{action_id}"),
            action_cost=action_cost,
            target_latent=_row_value(
                row,
                "target_latent",
                default=DEFAULT_ACTION_TARGET_LATENTS.get(action_id, "unknown"),
            ),
            description=_row_value(row, "description", default="Generated DS action"),
        )

    interactions_inserted = 0
    for row in interactions:
        source_customer_id = int(row["customer_id"])
        db_customer_id = customer_id_map.get(source_customer_id)
        customer_row = customer_rows_by_source_id.get(source_customer_id)
        if db_customer_id is None or customer_row is None:
            raise ValueError(
                f"Interaction references unknown generated customer {source_customer_id}"
            )
        action_id = int(row["action_id"])
        interaction_id = db_log_interaction(
            db,
            simulation_id=simulation_id,
            customer_id=db_customer_id,
            action_id=action_id,
            round_number=int(row["round_number"]),
            context_vector_bytes=_context_vector_from_payload(row, customer_row),
            ucb_score=float(_row_value(row, "ucb_score", default=0.0)),
            cost=float(_row_value(row, "cost", default=action_costs.get(action_id, 0.0))),
        )
        interactions_inserted += 1
        if row.get("converted") is not None:
            db_observe_outcome(
                db,
                interaction_id=interaction_id,
                converted=bool(row["converted"]),
                revenue=float(_row_value(row, "revenue", default=0.0)),
                converted_at=_row_value(row, "converted_at"),
                observed_at=_row_value(row, "observed_at"),
            )

    for row in model_state:
        upsert_model_state(
            db,
            simulation_id=simulation_id,
            action_id=int(row["action_id"]),
            round_number=int(_row_value(row, "round_number", default=0)),
            n_pulls=int(_row_value(row, "n_pulls", default=0)),
            theta_bytes=_payload_to_bytes(_row_value(row, "theta_json", "theta_vector", "theta")),
            a_bytes=_payload_to_bytes(_row_value(row, "a_json", "a_matrix")),
            b_bytes=_payload_to_bytes(_row_value(row, "b_json", "b_vector")),
            alpha=float(_row_value(row, "alpha", default=simulation_data["alpha"])),
        )

    artifacts_stored = 0
    artifacts_stored += _store_records_artifact(
        db, simulation_id, "customers.csv", customers
    )
    artifacts_stored += _store_records_artifact(
        db, simulation_id, "customer_latents.csv", latents
    )
    artifacts_stored += _store_records_artifact(
        db, simulation_id, "actions.csv", actions
    )
    artifacts_stored += _store_records_artifact(
        db, simulation_id, "interactions.csv", interactions
    )
    artifacts_stored += _store_records_artifact(
        db, simulation_id, "model_state.csv", model_state
    )

    for artifact in artifacts:
        if artifact.get("payload_json") is None and artifact.get("payload_text") is None:
            raise ValueError(
                f"Artifact {artifact.get('artifact_name', '<unknown>')} has no payload."
            )
        db_upsert_simulation_artifact(
            db,
            simulation_id=simulation_id,
            artifact_name=artifact["artifact_name"],
            artifact_type=artifact.get("artifact_type") or "json",
            content_type=artifact.get("content_type") or "application/json",
            payload_json=_json_ready(artifact.get("payload_json")),
            payload_text=artifact.get("payload_text"),
        )
        artifacts_stored += 1

    completed = bool(data.get("complete_simulation", True))
    if completed:
        complete_simulation(db, simulation_id)

    return {
        "simulation_id": simulation_id,
        "sim_name": sim_name,
        "customers_inserted": len(customers),
        "actions_upserted": len(actions),
        "interactions_inserted": interactions_inserted,
        "model_state_rows_upserted": len(model_state),
        "artifacts_stored": artifacts_stored,
        "completed": completed,
    }


def list_ds_artifacts(db: SQLHandler, simulation_id: int) -> list[dict[str, Any]] | None:
    if not _simulation_exists(db, simulation_id):
        return None
    df = db_list_simulation_artifacts(db, simulation_id)
    return [_serialize_record(row) for row in df.to_dict(orient="records")]


def get_ds_artifact(
    db: SQLHandler,
    simulation_id: int,
    artifact_name: str,
) -> dict[str, Any] | None:
    if not _simulation_exists(db, simulation_id):
        return None
    artifact = db_get_simulation_artifact(db, simulation_id, artifact_name)
    return _serialize_record(artifact)


def _get_feature_scales(db: SQLHandler, simulation_id: int) -> np.ndarray:
    context_df = db.select(
        """
        SELECT DISTINCT
            c.customer_id,
            c.recency,
            c.frequency,
            c.monetary,
            c.basket_diversity,
            c.avg_order_size,
            c.purchase_regularity
        FROM public.customers AS c
        JOIN public.interactions AS i
            ON i.customer_id = c.customer_id
        WHERE i.simulation_id = %s
        ORDER BY c.customer_id
        """,
        (simulation_id,),
    )

    if context_df.empty:
        context_df = db.select(
            """
            SELECT
                customer_id,
                recency,
                frequency,
                monetary,
                basket_diversity,
                avg_order_size,
                purchase_regularity
            FROM public.customers
            ORDER BY customer_id
            """
        )

    if context_df.empty:
        return np.ones(len(MODEL_FEATURE_COLUMNS), dtype=np.float64)

    matrix = context_df.loc[:, list(MODEL_FEATURE_COLUMNS)].to_numpy(dtype=np.float64)
    scales = np.max(np.abs(matrix), axis=0)
    return np.where(scales < 1e-8, 1.0, scales)


def _build_empty_bandit_state(
    action_rows: list[dict[str, Any]],
    *,
    alpha: float,
    context_dim: int,
) -> dict[int, dict[str, Any]]:
    state: dict[int, dict[str, Any]] = {}
    for action in action_rows:
        action_id = int(action["action_id"])
        state[action_id] = {
            "action_id": action_id,
            "action_name": str(action["action_name"]),
            "cost": float(action["action_cost"]),
            "alpha": float(alpha),
            "a_matrix": np.eye(context_dim, dtype=np.float64),
            "b_vector": np.zeros(context_dim, dtype=np.float64),
            "n_pulls": 0,
        }
    return state


def _theta_from_state(entry: dict[str, Any]) -> np.ndarray:
    return np.linalg.solve(entry["a_matrix"], entry["b_vector"])


def _reconstruct_bandit_state(db: SQLHandler, simulation_id: int) -> dict[str, Any] | None:
    simulation = _get_simulation_record(db, simulation_id)
    if simulation is None:
        return None

    action_rows = list_actions(db)
    context_dim = _normalize_context_dim(simulation.get("context_dim"))
    scales = _get_feature_scales(db, simulation_id)
    state = _build_empty_bandit_state(
        action_rows,
        alpha=float(simulation["alpha"]),
        context_dim=context_dim,
    )

    observed_rows = _fetchall_raw(
        db,
        """
        SELECT
            interaction_id,
            action_id,
            round_number,
            context_vector,
            reward,
            observed_at
        FROM public.interactions
        WHERE simulation_id = %s
          AND observed_at IS NOT NULL
        ORDER BY observed_at, interaction_id
        """,
        (simulation_id,),
    )

    latest_observed_at = None
    for row in observed_rows:
        action_id = int(row["action_id"])
        if action_id not in state:
            continue

        raw_context = _decode_context_vector(row["context_vector"], context_dim)
        scaled_context = raw_context / scales[:context_dim]
        reward = float(row["reward"] or 0.0)
        entry = state[action_id]
        entry["a_matrix"] += np.outer(scaled_context, scaled_context)
        entry["b_vector"] += reward * scaled_context
        entry["n_pulls"] += 1
        latest_observed_at = row["observed_at"]

    return {
        "simulation": simulation,
        "context_dim": context_dim,
        "feature_scales": scales[:context_dim],
        "actions": state,
        "updated_at": latest_observed_at,
    }


def get_model_state_snapshot(db: SQLHandler, simulation_id: int) -> dict[str, Any] | None:
    state = _reconstruct_bandit_state(db, simulation_id)
    if state is None:
        return None

    simulation = state["simulation"]
    actions = state["actions"]
    feature_names = list(MODEL_FEATURE_COLUMNS[: state["context_dim"]])

    theta = {
        feature_name: {
            entry["action_name"]: round(float(_theta_from_state(entry)[feature_index]), 6)
            for _, entry in sorted(actions.items())
        }
        for feature_index, feature_name in enumerate(feature_names)
    }

    return {
        "simulation_id": simulation_id,
        "alpha": float(simulation["alpha"]),
        "round_number": int(simulation.get("rounds_completed") or 0),
        "updated_at": _serialize_value(state["updated_at"]),
        "n_pulls": {
            entry["action_name"]: int(entry["n_pulls"])
            for _, entry in sorted(actions.items())
        },
        "theta": theta,
    }


def _decision_scores_with_metadata(
    db: SQLHandler,
    simulation_id: int,
    customer_id: int,
) -> list[dict[str, Any]] | None:
    state = _reconstruct_bandit_state(db, simulation_id)
    if state is None or not _customer_exists(db, customer_id):
        return None

    raw_context = _get_customer_feature_vector(db, customer_id)
    if raw_context is None:
        return None

    scaled_context = raw_context[: state["context_dim"]] / state["feature_scales"]
    scores: list[dict[str, Any]] = []

    for _, entry in sorted(state["actions"].items()):
        theta = _theta_from_state(entry)
        exploit = float(theta @ scaled_context)
        uncertainty = float(scaled_context @ np.linalg.solve(entry["a_matrix"], scaled_context))
        explore = float(entry["alpha"] * np.sqrt(max(uncertainty, 0.0)))
        scores.append(
            {
                "action": entry["action_name"],
                "action_id": entry["action_id"],
                "cost": float(entry["cost"]),
                "exploit": exploit,
                "explore": explore,
                "ucb_score": exploit + explore,
                "raw_context": raw_context[: state["context_dim"]],
            }
        )

    scores.sort(
        key=lambda row: (-row["ucb_score"], -row["exploit"], row["action_id"]),
    )
    return scores


def score_customer_actions(
    db: SQLHandler,
    simulation_id: int,
    customer_id: int,
) -> list[dict[str, Any]] | None:
    scores = _decision_scores_with_metadata(db, simulation_id, customer_id)
    if scores is None:
        return None

    return [
        {
            "action": row["action"],
            "exploit": row["exploit"],
            "explore": row["explore"],
            "ucb_score": row["ucb_score"],
            "cost": row["cost"],
        }
        for row in scores
    ]


def log_scored_decision(
    db: SQLHandler,
    simulation_id: int,
    customer_id: int,
    *,
    round_number: int | None = None,
) -> dict[str, Any] | None:
    if not _simulation_exists(db, simulation_id) or not _customer_exists(db, customer_id):
        return None

    scores = _decision_scores_with_metadata(db, simulation_id, customer_id)
    if not scores:
        return None

    selected = scores[0]
    next_round = round_number
    if next_round is None:
        result = _select_one(
            db,
            """
            SELECT COALESCE(MAX(round_number), 0) + 1 AS next_round
            FROM public.interactions
            WHERE simulation_id = %s
            """,
            (simulation_id,),
        )
        next_round = int(result["next_round"])

    result = _select_one(
        db,
        """
        SELECT sp_log_interaction(
            %s, %s, %s, %s, %s, %s, %s
        ) AS interaction_id
        """,
        (
            simulation_id,
            customer_id,
            selected["action_id"],
            int(next_round),
            _array_to_bytes(selected["raw_context"]),
            selected["ucb_score"],
            selected["cost"],
        ),
    )
    if result is None:
        return None

    db.commit()
    return {
        "interaction_id": int(result["interaction_id"]),
        "recommended_action": selected["action"],
        "scores": [
            {
                "action": row["action"],
                "exploit": row["exploit"],
                "explore": row["explore"],
                "ucb_score": row["ucb_score"],
                "cost": row["cost"],
            }
            for row in scores
        ],
    }


def submit_feedback(db: SQLHandler, payload: FeedbackRequest) -> dict[str, Any] | None:
    data = _dump_model(payload)

    interaction = _fetchone_raw(
        db,
        """
        SELECT
            interaction_id,
            simulation_id,
            action_id,
            observed_at
        FROM public.interactions
        WHERE interaction_id = %s
        """,
        (data["interaction_id"],),
    )
    if interaction is None:
        return None
    if interaction["observed_at"] is not None:
        raise ConflictError(
            f"Interaction {data['interaction_id']} already has recorded feedback. "
            "Use /feedback only for a pending interaction created by POST /decide; "
            "generated DS experiment imports are already observed."
        )

    try:
        result = _select_one(
            db,
            """
            SELECT *
            FROM sp_submit_feedback(%s, %s, %s, %s, %s)
            """,
            (
                data["interaction_id"],
                data["converted"],
                data["revenue"],
                data.get("converted_at"),
                data.get("observed_at"),
            ),
        )
        if result is None:
            return None

        simulation_id = int(interaction["simulation_id"])
        action_id = int(interaction["action_id"])
        state = _reconstruct_bandit_state(db, simulation_id)
        if state is None:
            raise RuntimeError("Model state reconstruction failed after feedback update.")

        action_state = state["actions"].get(action_id)
        if action_state is None:
            raise RuntimeError(
                f"Action {action_id} is missing from reconstructed model state."
            )

        theta = _theta_from_state(action_state)
        upsert_model_state(
            db,
            simulation_id=simulation_id,
            action_id=action_id,
            round_number=int(action_state["n_pulls"]),
            n_pulls=int(action_state["n_pulls"]),
            theta_bytes=_array_to_bytes(theta),
            a_bytes=_array_to_bytes(action_state["a_matrix"]),
            b_bytes=_array_to_bytes(action_state["b_vector"]),
            alpha=float(state["simulation"]["alpha"]),
        )
    except Exception:
        db.rollback()
        raise

    return {
        "interaction_id": int(result["interaction_id"]),
        "reward": float(result["reward"]),
        "observed_at": result["observed_at"],
        "model_updated": True,
    }


def get_metrics_snapshot(db: SQLHandler, simulation_id: int) -> dict[str, Any] | None:
    simulation = _select_one(
        db,
        """
        SELECT completed_at
        FROM public.simulations
        WHERE simulation_id = %s
        """,
        (simulation_id,),
    )
    if simulation is None:
        return None

    rounds = _select_one(
        db,
        """
        SELECT COUNT(*)::int AS rounds_completed
        FROM public.interactions
        WHERE simulation_id = %s
        """,
        (simulation_id,),
    )
    reward = _select_one(
        db,
        """
        SELECT SUM(reward) AS cumulative_reward
        FROM public.interactions
        WHERE simulation_id = %s
            AND observed_at IS NOT NULL
        """,
        (simulation_id,),
    )
    pending = _select_one(
        db,
        """
        SELECT COUNT(*)::int AS pending_observations
        FROM public.interactions
        WHERE simulation_id = %s
            AND observed_at IS NULL
        """,
        (simulation_id,),
    )
    totals = _select_one(
        db,
        """
        SELECT
            COUNT(*) FILTER (
                WHERE converted IS TRUE
                    AND observed_at IS NOT NULL
            )::int AS conversions,
            COALESCE(
                SUM(revenue) FILTER (WHERE observed_at IS NOT NULL),
                0.0
            ) AS total_revenue,
            COALESCE(SUM(cost), 0.0) AS total_cost
        FROM public.interactions
        WHERE simulation_id = %s
        """,
        (simulation_id,),
    )
    cumulative_reward_series = [
        _serialize_record(row)
        for row in _fetchall_raw(
            db,
            """
            SELECT
                round_number AS round,
                SUM(reward) OVER (ORDER BY round_number) AS cumulative_reward
            FROM public.interactions
            WHERE simulation_id = %s
                AND observed_at IS NOT NULL
            ORDER BY round_number
            """,
            (simulation_id,),
        )
    ]
    action_distribution = [
        _serialize_record(row)
        for row in _fetchall_raw(
            db,
            """
            SELECT
                i.round_number AS round,
                a.action_name AS action
            FROM public.interactions AS i
            JOIN public.actions AS a
                ON i.action_id = a.action_id
            WHERE i.simulation_id = %s
            ORDER BY i.round_number
            """,
            (simulation_id,),
        )
    ]
    conversion_by_action = [
        _serialize_record(row)
        for row in _fetchall_raw(
            db,
            """
            SELECT
                a.action_name AS action,
                AVG(i.converted::int) FILTER (
                    WHERE i.observed_at IS NOT NULL
                ) AS conversion_rate,
                COUNT(*)::int AS n_pulls
            FROM public.interactions AS i
            JOIN public.actions AS a
                ON i.action_id = a.action_id
            WHERE i.simulation_id = %s
            GROUP BY a.action_name
            ORDER BY a.action_name
            """,
            (simulation_id,),
        )
    ]
    recent_interactions = [
        _serialize_record(row)
        for row in _fetchall_raw(
            db,
            """
            SELECT
                i.*,
                a.action_name AS action
            FROM public.interactions AS i
            JOIN public.actions AS a
                ON i.action_id = a.action_id
            WHERE i.simulation_id = %s
            ORDER BY i.decision_at DESC
            LIMIT 20
            """,
            (simulation_id,),
        )
    ]

    rounds_completed = int(rounds["rounds_completed"]) if rounds else 0
    cumulative_reward = reward["cumulative_reward"] if reward else None
    cumulative_reward = float(cumulative_reward) if cumulative_reward is not None else None
    avg_reward_per_round = (
        cumulative_reward / rounds_completed
        if cumulative_reward is not None and rounds_completed > 0
        else None
    )

    return {
        "simulation_id": simulation_id,
        "status": "completed" if simulation["completed_at"] is not None else "running",
        "rounds_completed": rounds_completed,
        "cumulative_reward": cumulative_reward,
        "avg_reward_per_round": avg_reward_per_round,
        "pending_observations": int(pending["pending_observations"]) if pending else 0,
        "cumulative_reward_series": cumulative_reward_series,
        "action_distribution": action_distribution,
        "conversion_by_action": conversion_by_action,
        "recent_interactions": recent_interactions,
        "total_interactions": rounds_completed,
        "conversions": int(totals["conversions"]) if totals else 0,
        "total_revenue": float(totals["total_revenue"]) if totals else 0.0,
        "total_cost": float(totals["total_cost"]) if totals else 0.0,
        "total_reward": cumulative_reward,
    }
