"""Database-backed CRUD helpers for the FastAPI backend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from psycopg2 import sql

try:
    from .SQLHandler import SQLHandler
    from .db_interactions import (
        complete_simulation,
        create_simulation,
        get_customer_by_id,
        get_customer_latents
    )
    from .metadata import CUSTOMER_FIELDS, LATENT_FIELDS
    from .schemas import CustomerCreate, CustomerUpdate, DecideRequest, FeedbackRequest, SimulationCreate
except ImportError:
    from SQLHandler import SQLHandler
    from db_interactions import (
        complete_simulation,
        create_simulation,
        get_customer_by_id,
        get_customer_latents
    )
    from metadata import CUSTOMER_FIELDS, LATENT_FIELDS
    from schemas import CustomerCreate, CustomerUpdate, DecideRequest, FeedbackRequest, SimulationCreate


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


def _action_exists(db: SQLHandler, action_id: int) -> bool:
    return _select_one(
        db,
        "SELECT action_id FROM public.actions WHERE action_id = %s",
        (action_id,),
    ) is not None


def _simulation_exists(db: SQLHandler, simulation_id: int) -> bool:
    return _select_one(
        db,
        "SELECT simulation_id FROM public.simulations WHERE simulation_id = %s",
        (simulation_id,),
    ) is not None


def get_customer_record(db: SQLHandler, customer_id: int) -> dict[str, Any] | None:
    customer = _serialize_record(get_customer_by_id(db, customer_id))
    if customer is None:
        return None

    latents = _serialize_record(get_customer_latents(db, customer_id))
    customer["latents"] = latents
    return customer


def list_customers(db: SQLHandler, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM public.view_customer_with_latents
        ORDER BY customer_id
        LIMIT %s OFFSET %s
    """
    df = db.select(query, (limit, offset))
    return [_split_customer_row(row) for row in df.to_dict(orient="records")]


# def create_customer_record(db: SQLHandleobserve_r, payload: CustomerCreate) -> dict[str, Any]:
#     data = _dump_model(payload)
#     latents = data.pop("latents", None)

#     customer_id = insert_customer(db, **data)
#     if latents:
#         insert_customer_latent(db, customer_id=customer_id, **latents)

#     return get_customer_record(db, customer_id)


def upsert_customer_record(
    db: SQLHandler,
    payload: CustomerCreate | CustomerUpdate,
    customer_id: int | None = None,
) -> dict[str, Any]:
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


# def _simulation_enrichment_sql() -> str:
#     return """
#         CASE
#             WHEN s.completed_at IS NOT NULL THEN 'completed'
#             ELSE 'running'
#         END AS status,
#         COUNT(i.interaction_id)::int AS rounds_completed,
#         CASE
#             WHEN COUNT(*) FILTER (WHERE i.observed_at IS NOT NULL) = 0 THEN NULL
#             ELSE COALESCE(SUM(i.reward) FILTER (WHERE i.observed_at IS NOT NULL), 0.0)
#         END AS cumulative_reward
#     """


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
        FROM view_simulation_summary
        ORDER BY simulation_id DESC
        """
    )
    return [_serialize_record(row) for row in df.to_dict(orient="records")]


def create_simulation_record(db: SQLHandler, payload: SimulationCreate) -> dict[str, Any]:
    data = _dump_model(payload)
    simulation_id = create_simulation(db, **data)
    return _get_simulation_record(db, simulation_id)


def complete_simulation_record(db: SQLHandler, simulation_id: int) -> dict[str, Any] | None:
    if not _simulation_exists(db, simulation_id):
        return None
    complete_simulation(db, simulation_id)
    return _get_simulation_record(db, simulation_id)


def _get_action_cost(db: SQLHandler, action_id: int) -> float | None:
    action = _select_one(
        db,
        "SELECT action_cost FROM public.actions WHERE action_id = %s",
        (action_id,),
    )
    if action is None:
        return None
    return float(action["action_cost"])


def log_decision(db: SQLHandler, payload: DecideRequest) -> dict[str, Any] | None:
    data = _dump_model(payload)

    result = _select_one(
        db,
        """
        SELECT sp_log_interaction(
            %s, %s, %s, %s, %s, %s, %s
        ) AS interaction_id
        """,
        (
            data["simulation_id"],
            data["customer_id"],
            data["action_id"],
            data["round_number"],
            json.dumps(data["context_vector"]).encode("utf-8"),
            data["ucb_score"],
            data.get("cost"),
        ),
    )

    if result is None:
        return None

    return {
        "interaction_id": result["interaction_id"],
        "recommended_action_id": data["action_id"],
    }

def submit_feedback(db: SQLHandler, payload: FeedbackRequest) -> dict[str, Any] | None:
    data = _dump_model(payload)

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

    db.commit()
    return result


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
