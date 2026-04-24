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
        get_customer_latents,
        insert_customer,
        insert_customer_latent,
        log_interaction,
        observe_outcome,
    )
    from .metadata import CUSTOMER_FIELDS, LATENT_FIELDS
    from .schemas import CustomerCreate, CustomerUpdate, DecideRequest, FeedbackRequest, SimulationCreate
except ImportError:
    from SQLHandler import SQLHandler
    from db_interactions import (
        complete_simulation,
        create_simulation,
        get_customer_by_id,
        get_customer_latents,
        insert_customer,
        insert_customer_latent,
        log_interaction,
        observe_outcome,
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
        SELECT
            c.customer_id,
            c.gender,
            c.segment_label,
            c.recency,
            c.frequency,
            c.monetary,
            c.basket_diversity,
            c.avg_order_size,
            c.purchase_regularity,
            c.created_at,
            l.z_price_sensitivity,
            l.z_brand_loyalty,
            l.z_impulse_tendency
        FROM public.customers AS c
        LEFT JOIN public.customer_latents AS l
            ON l.customer_id = c.customer_id
        ORDER BY c.customer_id
        LIMIT %s OFFSET %s
    """
    df = db.select(query, (limit, offset))
    return [_split_customer_row(row) for row in df.to_dict(orient="records")]


def create_customer_record(db: SQLHandler, payload: CustomerCreate) -> dict[str, Any]:
    data = _dump_model(payload)
    latents = data.pop("latents", None)

    customer_id = insert_customer(db, **data)
    if latents:
        insert_customer_latent(db, customer_id=customer_id, **latents)

    return get_customer_record(db, customer_id)


def update_customer_record(
    db: SQLHandler,
    customer_id: int,
    payload: CustomerUpdate,
) -> dict[str, Any] | None:
    if get_customer_by_id(db, customer_id) is None:
        return None

    data = _dump_model(payload, exclude_unset=True)
    latents = data.pop("latents", None)

    customer_fields = [field for field in CUSTOMER_FIELDS if field in data]
    if customer_fields:
        assignments = [sql.SQL("{} = %s").format(sql.Identifier(field)) for field in customer_fields]
        query = sql.SQL("UPDATE public.customers SET {} WHERE customer_id = %s").format(
            sql.SQL(", ").join(assignments)
        )
        values = [data[field] for field in customer_fields] + [customer_id]
        db.cursor.execute(query, values)

    if latents:
        latent_fields = [field for field in LATENT_FIELDS if field in latents]
        columns = [sql.Identifier("customer_id")] + [sql.Identifier(field) for field in latent_fields]
        placeholders = sql.SQL(", ").join([sql.Placeholder()] * (len(latent_fields) + 1))
        updates = sql.SQL(", ").join(
            [
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(field), sql.Identifier(field))
                for field in latent_fields
            ]
        )
        query = sql.SQL(
            """
            INSERT INTO public.customer_latents ({columns})
            VALUES ({placeholders})
            ON CONFLICT (customer_id) DO UPDATE SET {updates}
            """
        ).format(
            columns=sql.SQL(", ").join(columns),
            placeholders=placeholders,
            updates=updates,
        )
        db.cursor.execute(query, [customer_id] + [latents[field] for field in latent_fields])

    if customer_fields or latents:
        db.commit()

    return get_customer_record(db, customer_id)


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


def _simulation_enrichment_sql() -> str:
    return """
        CASE
            WHEN s.completed_at IS NOT NULL THEN 'completed'
            ELSE 'running'
        END AS status,
        COUNT(i.interaction_id)::int AS rounds_completed,
        CASE
            WHEN COUNT(*) FILTER (WHERE i.observed_at IS NOT NULL) = 0 THEN NULL
            ELSE COALESCE(SUM(i.reward) FILTER (WHERE i.observed_at IS NOT NULL), 0.0)
        END AS cumulative_reward
    """


def _get_simulation_record(db: SQLHandler, simulation_id: int) -> dict[str, Any] | None:
    return _select_one(
        db,
        f"""
        SELECT
            s.simulation_id,
            s.sim_name,
            s.num_rounds,
            s.num_customers,
            s.alpha,
            s.context_dim,
            s.conversion_window_hours,
            s.notes,
            s.started_at,
            s.completed_at,
            {_simulation_enrichment_sql()}
        FROM public.simulations AS s
        LEFT JOIN public.interactions AS i
            ON i.simulation_id = s.simulation_id
        WHERE s.simulation_id = %s
        GROUP BY
            s.simulation_id,
            s.sim_name,
            s.num_rounds,
            s.num_customers,
            s.alpha,
            s.context_dim,
            s.conversion_window_hours,
            s.notes,
            s.started_at,
            s.completed_at
        """,
        (simulation_id,),
    )


def list_simulations(db: SQLHandler) -> list[dict[str, Any]]:
    df = db.select(
        f"""
        SELECT
            s.simulation_id,
            s.sim_name,
            s.num_rounds,
            s.num_customers,
            s.alpha,
            s.context_dim,
            s.conversion_window_hours,
            s.notes,
            s.started_at,
            s.completed_at,
            {_simulation_enrichment_sql()}
        FROM public.simulations AS s
        LEFT JOIN public.interactions AS i
            ON i.simulation_id = s.simulation_id
        GROUP BY
            s.simulation_id,
            s.sim_name,
            s.num_rounds,
            s.num_customers,
            s.alpha,
            s.context_dim,
            s.conversion_window_hours,
            s.notes,
            s.started_at,
            s.completed_at
        ORDER BY s.simulation_id DESC
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

    if get_customer_by_id(db, data["customer_id"]) is None:
        return None
    if not _simulation_exists(db, data["simulation_id"]):
        return None
    if not _action_exists(db, data["action_id"]):
        return None

    cost = data["cost"]
    if cost is None:
        cost = _get_action_cost(db, data["action_id"])

    interaction_id = log_interaction(
        db=db,
        simulation_id=data["simulation_id"],
        customer_id=data["customer_id"],
        action_id=data["action_id"],
        round_number=data["round_number"],
        context_vector_bytes=json.dumps(data["context_vector"]).encode("utf-8"),
        ucb_score=data["ucb_score"],
        cost=cost or 0.0,
    )

    return {
        "interaction_id": interaction_id,
        "recommended_action_id": data["action_id"],
        "placeholder": True,
        "stored_context_encoding": "json-bytes",
        "note": "This placeholder endpoint logs the caller-supplied action until DS model scoring is integrated.",
    }


def submit_feedback(db: SQLHandler, payload: FeedbackRequest) -> dict[str, Any] | None:
    data = _dump_model(payload)
    existing = _select_one(
        db,
        """
        SELECT interaction_id, converted, revenue, reward, observed_at
        FROM public.interactions
        WHERE interaction_id = %s
        """,
        (data["interaction_id"],),
    )
    if existing is None:
        return None

    observed_at = data.get("observed_at") or datetime.now(timezone.utc)
    converted_at = data.get("converted_at") if data["converted"] else None

    observe_outcome(
        db=db,
        interaction_id=data["interaction_id"],
        converted=data["converted"],
        revenue=data["revenue"],
        converted_at=converted_at,
        observed_at=observed_at,
    )

    return _select_one(
        db,
        """
        SELECT interaction_id, converted, revenue, reward, observed_at
        FROM public.interactions
        WHERE interaction_id = %s
        """,
        (data["interaction_id"],),
    )


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
