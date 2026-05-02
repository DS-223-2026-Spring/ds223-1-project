"""Database-backed CRUD helpers for the FastAPI backend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import numpy as np

try:
    from .SQLHandler import SQLHandler
    from .db_interactions import (
        complete_simulation,
        create_simulation,
        get_customer_by_id,
        get_customer_latents,
        upsert_model_state,
    )
    from .schemas import CustomerCreate, CustomerUpdate, FeedbackRequest, SimulationCreate
except ImportError:
    from SQLHandler import SQLHandler
    from db_interactions import (
        complete_simulation,
        create_simulation,
        get_customer_by_id,
        get_customer_latents,
        upsert_model_state,
    )
    from schemas import CustomerCreate, CustomerUpdate, FeedbackRequest, SimulationCreate


MODEL_FEATURE_COLUMNS = (
    "recency",
    "frequency",
    "monetary",
    "basket_diversity",
    "avg_order_size",
    "purchase_regularity",
)


class ConflictError(Exception):
    """Raised when a request conflicts with existing persisted state."""


def _dump_model(model: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True, exclude_unset=exclude_unset)
    return model.dict(exclude_none=True, exclude_unset=exclude_unset)


def _serialize_value(value: Any) -> Any:
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
            f"Interaction {data['interaction_id']} already has recorded feedback."
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
    if not _simulation_exists(db, simulation_id):
        return None

    metrics = _select_one(
        db,
        """
        SELECT
            %s AS simulation_id,
            COUNT(*)::int AS total_interactions,
            COUNT(*) FILTER (WHERE converted IS TRUE)::int AS conversions,
            COALESCE(SUM(revenue), 0.0) AS total_revenue,
            COALESCE(SUM(cost), 0.0) AS total_cost,
            COALESCE(SUM(reward), 0.0) AS total_reward
        FROM public.interactions
        WHERE simulation_id = %s
        """,
        (simulation_id, simulation_id),
    )

    return {
        "simulation_id": simulation_id,
        "total_interactions": metrics["total_interactions"] if metrics else 0,
        "conversions": metrics["conversions"] if metrics else 0,
        "total_revenue": float(metrics["total_revenue"]) if metrics else 0.0,
        "total_cost": float(metrics["total_cost"]) if metrics else 0.0,
        "total_reward": float(metrics["total_reward"]) if metrics else 0.0,
    }
