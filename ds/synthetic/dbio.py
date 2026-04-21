"""DB integration helpers that persist DS artifacts through db_interactions."""

from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .config import FEATURE_COLUMNS, SyntheticDataConfig
from .pipeline import SyntheticArtifacts


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
    """Persist generated DS artifacts into PostgreSQL via the DB CRUD layer."""

    db_crud, sql_handler_cls = _load_db_modules()
    db = _connect(sql_handler_cls)

    try:
        simulation_id = db_crud.create_simulation(
            db,
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
            db=db,
            customers=artifacts.customers,
            customer_latents=artifacts.customer_latents,
        )
        _persist_interactions(
            db_crud=db_crud,
            db=db,
            interactions=artifacts.interactions,
            customers=artifacts.customers,
            customer_id_map=customer_id_map,
            simulation_id=simulation_id,
        )
        _persist_model_state(
            db_crud=db_crud,
            db=db,
            model_state=artifacts.model_state,
            simulation_id=simulation_id,
        )
        db_crud.complete_simulation(db, simulation_id)
    finally:
        db.close()

    return DatabasePersistenceResult(
        simulation_id=simulation_id,
        customers_inserted=len(artifacts.customers),
        interactions_inserted=len(artifacts.interactions),
        model_state_rows_upserted=len(artifacts.model_state),
    )


def _persist_customers_and_latents(
    db_crud,
    db,
    customers: pd.DataFrame,
    customer_latents: pd.DataFrame,
) -> dict[int, int]:
    """Insert generated customers and latents, returning synthetic->DB id mapping."""

    latents_by_customer = customer_latents.set_index("customer_id").to_dict("index")
    customer_id_map: dict[int, int] = {}

    for row in customers.itertuples(index=False):
        synthetic_customer_id = int(row.customer_id)
        db_customer_id = db_crud.insert_customer(
            db,
            gender=_customer_gender(row, synthetic_customer_id),
            segment_label=row.segment,
            recency=row.recency,
            frequency=row.frequency,
            monetary=row.monetary,
            basket_diversity=row.basket_diversity,
            avg_order_size=row.avg_order_size,
            purchase_regularity=row.purchase_regularity,
        )
        customer_id_map[synthetic_customer_id] = db_customer_id

        latent_row = latents_by_customer[synthetic_customer_id]
        db_crud.insert_customer_latent(
            db,
            customer_id=db_customer_id,
            z_price_sensitivity=latent_row["z_price_sensitivity"],
            z_brand_loyalty=latent_row["z_brand_loyalty"],
            z_impulse_tendency=latent_row["z_impulse_tendency"],
        )

    return customer_id_map


def _persist_interactions(
    db_crud,
    db,
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
            db,
            simulation_id=simulation_id,
            customer_id=db_customer_id,
            action_id=int(row.action_id),
            round_number=int(row.round_number),
            context_vector_bytes=context_vector_bytes,
            ucb_score=_interaction_score(row),
            cost=float(row.cost),
        )

        observed_at = datetime.now(UTC).replace(tzinfo=None)
        converted_at = observed_at if bool(row.converted) else None
        db_crud.observe_outcome(
            db,
            interaction_id=interaction_id,
            converted=bool(row.converted),
            revenue=float(row.revenue),
            converted_at=converted_at,
            observed_at=observed_at,
        )


def _persist_model_state(
    db_crud,
    db,
    model_state: pd.DataFrame,
    simulation_id: int,
) -> None:
    """Persist placeholder model state via CRUD."""

    for row in model_state.itertuples(index=False):
        theta_bytes = _json_array_to_bytes(row.theta_json)
        a_bytes = _json_array_to_bytes(row.a_json)
        b_bytes = _json_array_to_bytes(row.b_json)
        db_crud.upsert_model_state(
            db,
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


def _customer_gender(row, synthetic_customer_id: int) -> str:
    """Return a DB-valid gender value for generated customers."""

    gender = getattr(row, "gender", None)
    if gender in {"M", "F"}:
        return gender
    return "F" if synthetic_customer_id % 2 == 0 else "M"


def _interaction_score(row) -> float:
    """Return the decision score stored by the DB schema."""

    score = getattr(row, "ucb_score", None)
    if score is None or pd.isna(score):
        return 0.0
    return float(score)


def _connect(sql_handler_cls):
    """Create a SQLHandler from the standard project DB environment."""

    return sql_handler_cls(
        host=os.getenv("DB_HOST", "db"),
        dbname=os.getenv("POSTGRES_DB", "campaign"),
        user=os.getenv("POSTGRES_USER", "campaign_user"),
        password=os.getenv("POSTGRES_PASSWORD", "campaign_pass"),
        port=int(os.getenv("DB_PORT", "5432")),
    )


def _load_db_modules():
    """Load DB modules in Docker-mounted or local repository layouts."""

    _ensure_repo_db_path()
    errors: list[ImportError] = []

    for crud_module_name, handler_module_name in (
        ("db_interactions", "SQLHandler"),
        ("db.db_interactions", "db.SQLHandler"),
    ):
        try:
            db_crud = importlib.import_module(crud_module_name)
            sql_handler_module = importlib.import_module(handler_module_name)
            return db_crud, sql_handler_module.SQLHandler
        except ImportError as exc:
            errors.append(exc)

    raise ModuleNotFoundError(
        "DB persistence requires db_interactions.py, SQLHandler.py, and their "
        "Python dependencies to be importable. In Docker these files are "
        "mounted into /app by docker-compose."
    ) from errors[-1]


def _ensure_repo_db_path() -> None:
    """Expose repo-root db/ modules for local non-Docker runs."""

    db_dir = Path(__file__).resolve().parents[2] / "db"
    if db_dir.exists() and str(db_dir) not in sys.path:
        sys.path.insert(0, str(db_dir))
