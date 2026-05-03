"""CRUD layer (stateless Data Access Layer).

All functions require an SQLHandler instance.
"""

import json
from typing import Any

from loguru import logger

try:
    from .SQLHandler import SQLHandler
except ImportError:
    from SQLHandler import SQLHandler


def get_all_customers(db: SQLHandler):
    """
    Retrieve all customers from the database.

    Returns:
        List of customer rows (as pandas DataFrame or dicts depending on SQLHandler config)

    Assumptions:
        - Table: public.customers exists
        - No pagination applied (use carefully in production)
    """
    logger.info("Fetching all customers")
    return db.select("SELECT * FROM public.customers")


def get_customer_by_id(db: SQLHandler, customer_id: int):
    """
    Fetch a single customer by ID.

    Args:
        customer_id: Primary key of customer

    Returns:
        dict if found, else None
    """
    logger.info(f"Fetching customer_id={customer_id}")
    df = db.select(
        "SELECT * FROM public.customers WHERE customer_id = %s",
        (customer_id,),
    )
    return df.iloc[0].to_dict() if not df.empty else None


def get_customer_latents(db: SQLHandler, customer_id: int):
    """
    Fetch latent attributes associated with a customer.

    Assumptions:
        - One-to-one relationship: customer_latents.customer_id is unique

    Returns:
        dict or None
    """
    logger.info(f"Fetching latents for customer_id={customer_id}")
    df = db.select(
        "SELECT * FROM public.customer_latents WHERE customer_id = %s",
        (customer_id,),
    )
    return df.iloc[0].to_dict() if not df.empty else None


def insert_customer(
    db: SQLHandler,
    gender,
    segment_label,
    recency,
    frequency,
    monetary,
    basket_diversity,
    avg_order_size,
    purchase_regularity,
):
    """Insert one customer through the shared stored procedure."""

    return upsert_customer(
        db,
        customer_id=None,
        gender=gender,
        segment_label=segment_label,
        recency=recency,
        frequency=frequency,
        monetary=monetary,
        basket_diversity=basket_diversity,
        avg_order_size=avg_order_size,
        purchase_regularity=purchase_regularity,
    )


def insert_customer_latent(
    db: SQLHandler,
    customer_id,
    z_price_sensitivity,
    z_brand_loyalty,
    z_impulse_tendency,
):
    """Insert or replace latent debug attributes for one customer."""

    logger.info(f"Upserting customer latents customer_id={customer_id}")
    db.cursor.execute(
        """
        INSERT INTO public.customer_latents (
            customer_id,
            z_price_sensitivity,
            z_brand_loyalty,
            z_impulse_tendency
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (customer_id) DO UPDATE
        SET
            z_price_sensitivity = EXCLUDED.z_price_sensitivity,
            z_brand_loyalty = EXCLUDED.z_brand_loyalty,
            z_impulse_tendency = EXCLUDED.z_impulse_tendency
        """,
        (
            customer_id,
            z_price_sensitivity,
            z_brand_loyalty,
            z_impulse_tendency,
        ),
    )
    db.commit()


def upsert_customer(
    db: SQLHandler,
    customer_id,
    gender,
    segment_label,
    recency,
    frequency,
    monetary,
    basket_diversity,
    avg_order_size,
    purchase_regularity,
    z_price_sensitivity=None,
    z_brand_loyalty=None,
    z_impulse_tendency=None,
):
    """Insert or update one customer and optional latents through sp_upsert_customer."""

    logger.info(f"Upserting customer customer_id={customer_id}")
    db.cursor.execute(
        """
        SELECT public.sp_upsert_customer(
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        ) AS customer_id
        """,
        (
            customer_id,
            gender,
            segment_label,
            recency,
            frequency,
            monetary,
            basket_diversity,
            avg_order_size,
            purchase_regularity,
            z_price_sensitivity,
            z_brand_loyalty,
            z_impulse_tendency,
        ),
    )
    new_customer_id = db.cursor.fetchone()[0]
    db.commit()
    return new_customer_id


def upsert_action(
    db: SQLHandler,
    action_id,
    action_name,
    action_cost,
    target_latent,
    description,
):
    """Insert or update one seeded/generated action definition."""

    logger.info(f"Upserting action action_id={action_id}")
    db.cursor.execute(
        """
        INSERT INTO public.actions (
            action_id,
            action_name,
            action_cost,
            target_latent,
            description
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (action_id) DO UPDATE
        SET
            action_name = EXCLUDED.action_name,
            action_cost = EXCLUDED.action_cost,
            target_latent = EXCLUDED.target_latent,
            description = EXCLUDED.description
        """,
        (
            action_id,
            action_name,
            action_cost,
            target_latent,
            description,
        ),
    )
    db.commit()


def log_interaction(
    db: SQLHandler,
    simulation_id,
    customer_id,
    action_id,
    round_number,
    context_vector_bytes,
    ucb_score,
    cost,
):
    """Log one interaction through sp_log_interaction."""

    logger.info(
        f"Logging interaction sim={simulation_id}, customer={customer_id}, action={action_id}"
    )
    db.cursor.execute(
        """
        SELECT public.sp_log_interaction(%s, %s, %s, %s, %s, %s, %s)
        AS interaction_id
        """,
        (
            simulation_id,
            customer_id,
            action_id,
            round_number,
            context_vector_bytes,
            ucb_score,
            cost,
        ),
    )
    interaction_id = db.cursor.fetchone()[0]
    db.commit()
    return interaction_id


def observe_outcome(
    db: SQLHandler,
    interaction_id,
    converted,
    revenue,
    converted_at=None,
    observed_at=None,
):
    """Record one realized outcome through sp_submit_feedback."""

    logger.info(f"Observing outcome interaction_id={interaction_id}")
    db.cursor.execute(
        """
        SELECT *
        FROM public.sp_submit_feedback(%s, %s, %s, %s, %s)
        """,
        (
            interaction_id,
            converted,
            revenue,
            converted_at,
            observed_at,
        ),
    )
    row = db.cursor.fetchone()
    columns = [column.name for column in db.cursor.description]
    db.commit()
    return dict(zip(columns, row, strict=True))


def get_pending_interactions(db: SQLHandler, older_than_hours=48):
    """
    Retrieve interactions that have not been observed yet.

    Args:
        older_than_hours: threshold for filtering stale interactions

    Returns:
        DataFrame of pending interactions

    Assumptions:
        - interactions.observed_at is NULL until feedback is recorded
        - decision_at exists and is timestamp
    """
    logger.info(f"Fetching pending interactions older than {older_than_hours}h")
    return db.select(
        """
        SELECT *
        FROM public.interactions
        WHERE observed_at IS NULL
          AND decision_at < NOW() - (%s * INTERVAL '1 hour')
        """,
        (older_than_hours,),
    )


def get_model_state(db: SQLHandler, simulation_id: int, action_id: int):
    """
    Retrieve latest model state for a given simulation-action pair.

    Returns:
        dict or None

    Assumptions:
        - model_state stores sequential updates per round
    """
    logger.info(f"Fetching model state sim={simulation_id}, action={action_id}")
    df = db.select(
        """
        SELECT *
        FROM public.model_state
        WHERE simulation_id = %s AND action_id = %s
        ORDER BY round_number DESC
        LIMIT 1
        """,
        (simulation_id, action_id),
    )
    return df.iloc[0].to_dict() if not df.empty else None


def upsert_model_state(
    db: SQLHandler,
    simulation_id,
    action_id,
    round_number,
    n_pulls,
    theta_bytes,
    a_bytes,
    b_bytes,
    alpha,
):
    """
    Insert or update model state for a bandit / learning system.

    Behavior:
        - Uses ON CONFLICT (simulation_id, action_id, round_number)
        - Stores serialized matrix/vector state as bytes

    Assumptions:
        - Primary key constraint exists on (simulation_id, action_id, round_number)
    """
    logger.info(f"Upserting model state sim={simulation_id}, action={action_id}")
    db.cursor.execute(
        """
        INSERT INTO public.model_state
        (simulation_id, action_id, round_number, n_pulls,
         theta_vector, a_matrix, b_vector, alpha)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (simulation_id, action_id, round_number)
        DO UPDATE SET
            n_pulls = EXCLUDED.n_pulls,
            theta_vector = EXCLUDED.theta_vector,
            a_matrix = EXCLUDED.a_matrix,
            b_vector = EXCLUDED.b_vector,
            alpha = EXCLUDED.alpha,
            updated_at = NOW()
        """,
        (
            simulation_id,
            action_id,
            round_number,
            n_pulls,
            theta_bytes,
            a_bytes,
            b_bytes,
            alpha,
        ),
    )
    db.commit()
    logger.success("Model state updated")


def create_simulation(
    db: SQLHandler,
    sim_name,
    num_rounds,
    num_customers,
    alpha,
    context_dim=6,
    conversion_window_hours=48,
    notes=None,
):
    """
    Create a new simulation run.

    Returns:
        simulation_id (int)

    Assumptions:
        - simulations table exists
        - simulation_name is not necessarily unique
    """
    logger.info(f"Creating simulation {sim_name}")
    db.cursor.execute(
        """
        INSERT INTO public.simulations
        (sim_name, num_rounds, num_customers, alpha,
         context_dim, conversion_window_hours, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING simulation_id
        """,
        (
            sim_name,
            num_rounds,
            num_customers,
            alpha,
            context_dim,
            conversion_window_hours,
            notes,
        ),
    )

    simulation_id = db.cursor.fetchone()[0]
    db.commit()
    logger.success(f"Simulation created id={simulation_id}")
    return simulation_id


def complete_simulation(db: SQLHandler, simulation_id: int):
    """
    Mark simulation as completed.

    Behavior:
        - Sets completed_at = NOW()

    Returns:
        None
    """
    logger.info(f"Completing simulation id={simulation_id}")
    db.cursor.execute(
        """
        UPDATE public.simulations
        SET completed_at = NOW()
        WHERE simulation_id = %s
        """,
        (simulation_id,),
    )
    db.commit()
    logger.success("Simulation completed")


def ensure_simulation_artifacts_table(db: SQLHandler) -> None:
    """Create the DS artifact table for databases initialized before it existed."""

    db.cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS public.simulation_artifacts (
            artifact_id     SERIAL PRIMARY KEY,
            simulation_id   INTEGER NOT NULL
                            REFERENCES public.simulations(simulation_id)
                            ON DELETE CASCADE,
            artifact_name   VARCHAR(150) NOT NULL,
            artifact_type   VARCHAR(30) NOT NULL DEFAULT 'json',
            content_type    VARCHAR(100) NOT NULL DEFAULT 'application/json',
            payload_json    JSONB,
            payload_text    TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            CHECK (payload_json IS NOT NULL OR payload_text IS NOT NULL),
            UNIQUE (simulation_id, artifact_name)
        )
        """
    )
    db.cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_simulation_artifacts_simulation
            ON public.simulation_artifacts(simulation_id)
        """
    )
    db.commit()



def upsert_simulation_artifact(
    db: SQLHandler,
    simulation_id: int,
    artifact_name: str,
    artifact_type: str,
    content_type: str,
    payload_json: Any | None = None,
    payload_text: str | None = None,
) -> int:
    """Insert or update one generated DS artifact payload for a simulation."""

    ensure_simulation_artifacts_table(db)
    if payload_json is None and payload_text is None:
        raise ValueError("simulation artifact payload cannot be empty")

    logger.info(f"Upserting simulation artifact sim={simulation_id}, name={artifact_name}")
    db.cursor.execute(
        """
        INSERT INTO public.simulation_artifacts (
            simulation_id,
            artifact_name,
            artifact_type,
            content_type,
            payload_json,
            payload_text
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s)
        ON CONFLICT (simulation_id, artifact_name) DO UPDATE
        SET
            artifact_type = EXCLUDED.artifact_type,
            content_type = EXCLUDED.content_type,
            payload_json = EXCLUDED.payload_json,
            payload_text = EXCLUDED.payload_text,
            created_at = NOW()
        RETURNING artifact_id
        """,
        (
            simulation_id,
            artifact_name,
            artifact_type,
            content_type,
            json.dumps(payload_json) if payload_json is not None else None,
            payload_text,
        ),
    )
    artifact_id = db.cursor.fetchone()[0]
    db.commit()
    return artifact_id


def list_simulation_artifacts(db: SQLHandler, simulation_id: int):
    """List stored generated artifact payloads for one simulation."""

    ensure_simulation_artifacts_table(db)
    return db.select(
        """
        SELECT
            artifact_id,
            simulation_id,
            artifact_name,
            artifact_type,
            content_type,
            created_at
        FROM public.simulation_artifacts
        WHERE simulation_id = %s
        ORDER BY artifact_name
        """,
        (simulation_id,),
    )


def get_simulation_artifact(db: SQLHandler, simulation_id: int, artifact_name: str):
    """Fetch one generated artifact payload for a simulation."""

    ensure_simulation_artifacts_table(db)
    df = db.select(
        """
        SELECT
            artifact_id,
            simulation_id,
            artifact_name,
            artifact_type,
            content_type,
            payload_json,
            payload_text,
            created_at
        FROM public.simulation_artifacts
        WHERE simulation_id = %s
          AND artifact_name = %s
        """,
        (simulation_id, artifact_name),
    )
    return df.iloc[0].to_dict() if not df.empty else None
