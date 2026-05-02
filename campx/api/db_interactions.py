"""
CRUD layer (stateless Data Access Layer).

All functions require an SQLHandler instance.
"""

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
