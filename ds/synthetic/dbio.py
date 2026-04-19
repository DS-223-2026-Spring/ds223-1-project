"""DB integration helpers that persist DS artifacts through db.crud."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .config import FEATURE_COLUMNS, SyntheticDataConfig
from .pipeline import SyntheticArtifacts

try:
    from db import crud
    _CRUD_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local env
    crud = None
    _CRUD_IMPORT_ERROR = exc


@dataclass(slots=True)
class DatabasePersistenceResult:
    """Summary of one DS-to-DB persistence run."""

    simulation_id: int
    customers_inserted: int
    interactions_inserted: int
    model_state_rows_upserted: int


def persist_pipeline_artifacts_to_db(
    artifacts: SyntheticArtifacts,
    config: SyntheticDataConfig,
    notes: str | None = None,
) -> DatabasePersistenceResult:
    """Persist generated DS artifacts into PostgreSQL via the CRUD layer."""

    db_crud = _get_crud()
    simulation_id = db_crud.create_simulation(
        sim_name=config.simulation_id,
        num_rounds=config.n_rounds,
        num_customers=config.n_customers,
        alpha=config.alpha,
        context_dim=len(FEATURE_COLUMNS),
        conversion_window_hours=48,
        notes=notes,
    )

    customer_id_map = _persist_customers_and_latents(
        db_crud=db_crud,
        customers=artifacts.customers,
        customer_latents=artifacts.customer_latents,
    )
    _persist_interactions(
        db_crud=db_crud,
        interactions=artifacts.interactions,
        customers=artifacts.customers,
        customer_id_map=customer_id_map,
        simulation_id=simulation_id,
    )
    _persist_model_state(
        db_crud=db_crud,
        model_state=artifacts.model_state,
        simulation_id=simulation_id,
    )
    db_crud.complete_simulation(simulation_id)

    return DatabasePersistenceResult(
        simulation_id=simulation_id,
        customers_inserted=len(artifacts.customers),
        interactions_inserted=len(artifacts.interactions),
        model_state_rows_upserted=len(artifacts.model_state),
    )


def _persist_customers_and_latents(
    db_crud,
    customers: pd.DataFrame,
    customer_latents: pd.DataFrame,
) -> dict[int, int]:
    """Insert generated customers and latents, returning synthetic->DB id mapping."""

    latents_by_customer = customer_latents.set_index("customer_id").to_dict("index")
    customer_id_map: dict[int, int] = {}

    for row in customers.itertuples(index=False):
        db_customer_id = db_crud.insert_customer(
            gender=None,
            segment_label=row.segment,
            recency=row.recency,
            frequency=row.frequency,
            monetary=row.monetary,
            basket_diversity=row.basket_diversity,
            avg_order_size=row.avg_order_size,
            purchase_regularity=row.purchase_regularity,
        )
        customer_id_map[int(row.customer_id)] = db_customer_id

        latent_row = latents_by_customer[int(row.customer_id)]
        db_crud.insert_customer_latent(
            customer_id=db_customer_id,
            z_price_sensitivity=latent_row["z_price_sensitivity"],
            z_brand_loyalty=latent_row["z_brand_loyalty"],
            z_impulse_tendency=latent_row["z_impulse_tendency"],
        )

    return customer_id_map


def _persist_interactions(
    db_crud,
    interactions: pd.DataFrame,
    customers: pd.DataFrame,
    customer_id_map: dict[int, int],
    simulation_id: int,
) -> None:
    """Insert interactions via CRUD and immediately record observed outcomes."""

    customer_features = customers.set_index("customer_id")[FEATURE_COLUMNS]

    for row in interactions.itertuples(index=False):
        synthetic_customer_id = int(row.customer_id)
        db_customer_id = customer_id_map[synthetic_customer_id]
        context_vector_bytes = np.asarray(
            customer_features.loc[synthetic_customer_id].to_numpy(dtype=float),
            dtype=np.float64,
        ).tobytes()

        interaction_id = db_crud.log_interaction(
            simulation_id=simulation_id,
            customer_id=db_customer_id,
            action_id=int(row.action_id),
            round_number=int(row.round_number),
            context_vector_bytes=context_vector_bytes,
            ucb_score=None,
            cost=float(row.cost),
        )

        observed_at = datetime.now(UTC).replace(tzinfo=None)
        converted_at = observed_at if bool(row.converted) else None
        db_crud.observe_outcome(
            interaction_id=interaction_id,
            converted=bool(row.converted),
            revenue=float(row.revenue),
            converted_at=converted_at,
            observed_at=observed_at,
        )


def _persist_model_state(db_crud, model_state: pd.DataFrame, simulation_id: int) -> None:
    """Persist placeholder model state via CRUD."""

    for row in model_state.itertuples(index=False):
        theta_bytes = _json_array_to_bytes(row.theta_json)
        a_bytes = _json_array_to_bytes(row.a_json)
        b_bytes = _json_array_to_bytes(row.b_json)
        db_crud.upsert_model_state(
            simulation_id=simulation_id,
            action_id=int(row.action_id),
            round_number=0,
            n_pulls=int(row.n_pulls),
            theta_bytes=theta_bytes,
            a_bytes=a_bytes,
            b_bytes=b_bytes,
            alpha=float(row.alpha),
        )


def _json_array_to_bytes(payload: str) -> bytes:
    """Convert a JSON list payload into deterministic float64 bytes."""

    return np.asarray(json.loads(payload), dtype=np.float64).tobytes()


def _get_crud():
    """Return the CRUD module or raise a clear dependency error."""

    if crud is None:
        raise ModuleNotFoundError(
            "DB persistence requires the PostgreSQL driver. Install "
            "`psycopg2-binary` in the active Python environment to use --persist-db."
        ) from _CRUD_IMPORT_ERROR
    return crud
