"""CRUD layer (stateless Data Access Layer).

All functions require an SQLHandler instance.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from psycopg2.extras import execute_values

try:
    from .SQLHandler import SQLHandler
except ImportError:
    from SQLHandler import SQLHandler


DEFAULT_ACTION_TARGET_LATENTS = {
    0: "brand_loyalty",
    1: "price_sensitivity",
    2: "price_sensitivity+planning",
    3: "brand_loyalty+impulse",
    4: "impulse_tendency",
}


def _batch_timestamp(offset: int = 0) -> datetime:
    """Return a naive UTC timestamp suitable for project TIMESTAMP columns."""

    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        microseconds=offset
    )


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


def list_action_definitions(db: SQLHandler):
    """Return the seeded action catalog as plain dictionaries."""

    logger.info("Fetching action definitions")
    return db.fetch_all(
        """
        SELECT action_id, action_name, action_cost, target_latent, description
        FROM public.actions
        ORDER BY action_id
        """
    )


def get_simulation_summary(db: SQLHandler, simulation_id: int):
    """Fetch one simulation summary row from the shared summary view."""

    logger.info(f"Fetching simulation summary simulation_id={simulation_id}")
    return db.fetch_one(
        """
        SELECT *
        FROM public.view_simulation_summary
        WHERE simulation_id = %s
        """,
        (simulation_id,),
    )


def list_customer_feature_rows(db: SQLHandler, limit: int | None = None):
    """Fetch customer feature rows used for simulation context vectors."""

    logger.info(f"Fetching customer feature rows limit={limit}")
    if limit is None:
        return db.fetch_all(
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

    return db.fetch_all(
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
        LIMIT %s
        """,
        (limit,),
    )


def list_customer_simulation_rows(db: SQLHandler, limit: int | None = None):
    """Fetch customer feature and latent rows used by backend simulation."""

    logger.info(f"Fetching customer simulation rows limit={limit}")
    base_query = """
        SELECT
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
            z_impulse_tendency
        FROM public.view_customer_with_latents
        ORDER BY customer_id
    """
    if limit is None:
        return db.fetch_all(base_query)

    return db.fetch_all(f"{base_query} LIMIT %s", (limit,))


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


def bulk_upsert_actions(db: SQLHandler, actions: list[dict[str, Any]]) -> int:
    """Insert or update generated action definitions in one DB batch."""

    if not actions:
        return 0

    values = [
        (
            int(row["action_id"]),
            row.get("action_name") or f"action_{int(row['action_id'])}",
            float(row.get("action_cost") or row.get("base_cost") or 0.0),
            row.get("target_latent")
            or DEFAULT_ACTION_TARGET_LATENTS.get(int(row["action_id"]), "unknown"),
            row.get("description") or "Generated DS action",
        )
        for row in actions
    ]

    logger.info(f"Bulk upserting {len(values)} actions")
    execute_values(
        db.cursor,
        """
        INSERT INTO public.actions (
            action_id,
            action_name,
            action_cost,
            target_latent,
            description
        )
        VALUES %s
        ON CONFLICT (action_id) DO UPDATE
        SET
            action_name = EXCLUDED.action_name,
            action_cost = EXCLUDED.action_cost,
            target_latent = EXCLUDED.target_latent,
            description = EXCLUDED.description
        """,
        values,
        page_size=1000,
    )
    db.commit()
    return len(values)


def bulk_insert_customers_with_latents(
    db: SQLHandler,
    customer_rows: list[dict[str, Any]],
) -> dict[int, int]:
    """
    Insert generated customers and latents in table batches.

    Returns a mapping from source/generated customer_id to DB customer_id.
    """

    if not customer_rows:
        return {}

    values = []
    created_at_to_source_id: dict[datetime, int] = {}
    batch_time = _batch_timestamp()
    for offset, row in enumerate(customer_rows):
        source_customer_id = int(row.get("source_customer_id", row["customer_id"]))
        created_at = batch_time + timedelta(microseconds=offset)
        created_at_to_source_id[created_at] = source_customer_id
        values.append(
            (
                row.get("gender") or ("F" if source_customer_id % 2 == 0 else "M"),
                row.get("segment_label", row.get("segment")),
                float(row["recency"]),
                float(row["frequency"]),
                float(row["monetary"]),
                float(row["basket_diversity"]),
                float(row["avg_order_size"]),
                float(row["purchase_regularity"]),
                created_at,
            )
        )

    logger.info(f"Bulk inserting {len(values)} customers")
    inserted_rows = execute_values(
        db.cursor,
        """
        INSERT INTO public.customers (
            gender,
            segment_label,
            recency,
            frequency,
            monetary,
            basket_diversity,
            avg_order_size,
            purchase_regularity,
            created_at
        )
        VALUES %s
        RETURNING customer_id, created_at
        """,
        values,
        page_size=1000,
        fetch=True,
    )

    customer_id_map = {
        int(created_at_to_source_id[created_at]): int(customer_id)
        for customer_id, created_at in inserted_rows
    }

    latent_values = []
    for row in customer_rows:
        source_customer_id = int(row.get("source_customer_id", row["customer_id"]))
        if row.get("z_price_sensitivity") is None:
            continue
        latent_values.append(
            (
                customer_id_map[source_customer_id],
                float(row["z_price_sensitivity"]),
                float(row["z_brand_loyalty"]),
                float(row["z_impulse_tendency"]),
            )
        )

    if latent_values:
        logger.info(f"Bulk upserting {len(latent_values)} customer latent rows")
        execute_values(
            db.cursor,
            """
            INSERT INTO public.customer_latents (
                customer_id,
                z_price_sensitivity,
                z_brand_loyalty,
                z_impulse_tendency
            )
            VALUES %s
            ON CONFLICT (customer_id) DO UPDATE
            SET
                z_price_sensitivity = EXCLUDED.z_price_sensitivity,
                z_brand_loyalty = EXCLUDED.z_brand_loyalty,
                z_impulse_tendency = EXCLUDED.z_impulse_tendency
            """,
            latent_values,
            page_size=1000,
        )

    db.commit()
    return customer_id_map


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


def bulk_insert_interactions(db: SQLHandler, interactions: list[dict[str, Any]]) -> int:
    """
    Insert generated interaction rows in one or more DB batches.

    Generated DS imports already contain outcomes, so this writes the observed
    interaction state directly instead of logging and then submitting feedback
    row by row. Pending rows remain supported when converted is omitted.
    """

    if not interactions:
        return 0

    values = []
    batch_time = _batch_timestamp()
    for offset, row in enumerate(interactions):
        converted = row.get("converted")
        cost = float(row.get("cost") or 0.0)
        revenue = float(row.get("revenue", 0.0) or 0.0)
        observed_at = row.get("observed_at")
        converted_at = row.get("converted_at")
        reward = row.get("reward")

        if converted is not None:
            converted = bool(converted)
            observed_at = observed_at or batch_time + timedelta(microseconds=offset)
            converted_at = converted_at or (observed_at if converted else None)
            reward = revenue - cost if reward is None else float(reward)

        values.append(
            (
                int(row["simulation_id"]),
                int(row["customer_id"]),
                int(row["action_id"]),
                int(row["round_number"]),
                row["context_vector_bytes"],
                float(row.get("ucb_score") or 0.0),
                converted,
                revenue,
                cost,
                reward,
                converted_at,
                observed_at,
            )
        )

    logger.info(f"Bulk inserting {len(values)} interactions")
    execute_values(
        db.cursor,
        """
        INSERT INTO public.interactions (
            simulation_id,
            customer_id,
            action_id,
            round_number,
            context_vector,
            ucb_score,
            converted,
            revenue,
            cost,
            reward,
            converted_at,
            observed_at
        )
        VALUES %s
        """,
        values,
        page_size=1000,
    )
    db.commit()
    return len(values)


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


def get_interaction_summary(db: SQLHandler, interaction_id: int):
    """Fetch the interaction fields needed by feedback/model update flows."""

    logger.info(f"Fetching interaction summary interaction_id={interaction_id}")
    return db.fetch_one(
        """
        SELECT
            interaction_id,
            simulation_id,
            action_id,
            round_number,
            observed_at
        FROM public.interactions
        WHERE interaction_id = %s
        """,
        (interaction_id,),
    )


def get_next_simulation_round(db: SQLHandler, simulation_id: int) -> int:
    """Return the next round number for one simulation."""

    logger.info(f"Fetching next round number simulation_id={simulation_id}")
    row = db.fetch_one(
        """
        SELECT COALESCE(MAX(round_number), 0) + 1 AS next_round
        FROM public.interactions
        WHERE simulation_id = %s
        """,
        (simulation_id,),
    )
    return int(row["next_round"]) if row is not None else 1


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


def list_observed_simulation_interactions(db: SQLHandler, simulation_id: int):
    """Return observed interactions in replay order for state reconstruction."""

    logger.info(f"Fetching observed interactions simulation_id={simulation_id}")
    return db.fetch_all(
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


def bulk_upsert_model_state(
    db: SQLHandler,
    model_state_rows: list[dict[str, Any]],
) -> int:
    """Insert or update generated model-state rows in one DB batch."""

    if not model_state_rows:
        return 0

    values = [
        (
            int(row["simulation_id"]),
            int(row["action_id"]),
            int(row.get("round_number", 0)),
            int(row.get("n_pulls", 0)),
            row["theta_bytes"],
            row["a_bytes"],
            row["b_bytes"],
            float(row["alpha"]),
        )
        for row in model_state_rows
    ]

    logger.info(f"Bulk upserting {len(values)} model state rows")
    execute_values(
        db.cursor,
        """
        INSERT INTO public.model_state (
            simulation_id,
            action_id,
            round_number,
            n_pulls,
            theta_vector,
            a_matrix,
            b_vector,
            alpha
        )
        VALUES %s
        ON CONFLICT (simulation_id, action_id, round_number)
        DO UPDATE SET
            n_pulls = EXCLUDED.n_pulls,
            theta_vector = EXCLUDED.theta_vector,
            a_matrix = EXCLUDED.a_matrix,
            b_vector = EXCLUDED.b_vector,
            alpha = EXCLUDED.alpha,
            updated_at = NOW()
        """,
        values,
        page_size=1000,
    )
    db.commit()
    return len(values)


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
