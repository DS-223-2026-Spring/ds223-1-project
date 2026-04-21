"""
CRUD layer (stateless Data Access Layer)

All functions require an SQLHandler instance.

This module isolates all database operations for:
- customers
- interactions
- model state
- simulations

Used by:
- ETL pipelines
- ML bandit engine
- API layer
"""

from SQLHandler import SQLHandler
from loguru import logger


def get_all_customers(db: SQLHandler):
    """
    Fetch all customers from the database.

    Returns:
        DataFrame: all customer rows
    """
    logger.info("Fetching all customers")
    return db.select("SELECT * FROM public.customers")


def get_customer_by_id(db: SQLHandler, customer_id: int):
    """
    Fetch a single customer by ID.

    Args:
        customer_id (int): customer primary key

    Returns:
        dict | None: customer row as dictionary or None if not found
    """
    logger.info(f"Fetching customer_id={customer_id}")

    df = db.select(
        "SELECT * FROM public.customers WHERE customer_id = %s",
        (customer_id,)
    )

    return df.iloc[0].to_dict() if not df.empty else None


def get_customer_latents(db: SQLHandler, customer_id: int):
    """
    Fetch latent behavioral traits for a customer.

    Used for simulation and bandit context generation.

    Args:
        customer_id (int)

    Returns:
        dict | None: latent vector or None
    """
    logger.info(f"Fetching latents for customer_id={customer_id}")

    df = db.select(
        "SELECT * FROM public.customer_latents WHERE customer_id = %s",
        (customer_id,)
    )

    return df.iloc[0].to_dict() if not df.empty else None


def insert_customer(db: SQLHandler, gender, segment_label, recency,
                    frequency, monetary, basket_diversity,
                    avg_order_size, purchase_regularity):
    """
    Insert a new customer into the customers table.

    Returns:
        int: generated customer_id
    """
    logger.info("Inserting new customer")

    db.cursor.execute("""
        INSERT INTO public.customers
        (gender, segment_label, recency, frequency, monetary,
         basket_diversity, avg_order_size, purchase_regularity)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING customer_id
    """, (
        gender, segment_label, recency, frequency, monetary,
        basket_diversity, avg_order_size, purchase_regularity
    ))

    cid = db.cursor.fetchone()[0]
    db.commit()

    logger.success(f"Inserted customer_id={cid}")
    return cid


def insert_customer_latent(db: SQLHandler, customer_id,
                           z_price_sensitivity,
                           z_brand_loyalty,
                           z_impulse_tendency):
    """
    Insert latent behavioral traits for a customer.

    Args:
        customer_id (int)
        z_price_sensitivity (float)
        z_brand_loyalty (float)
        z_impulse_tendency (float)
    """
    logger.info(f"Inserting latents for customer_id={customer_id}")

    db.cursor.execute("""
        INSERT INTO public.customer_latents
        (customer_id, z_price_sensitivity, z_brand_loyalty, z_impulse_tendency)
        VALUES (%s,%s,%s,%s)
    """, (
        customer_id,
        z_price_sensitivity,
        z_brand_loyalty,
        z_impulse_tendency
    ))

    db.commit()
    logger.success("Latents inserted")



def log_interaction(db: SQLHandler, simulation_id, customer_id,
                    action_id, round_number,
                    context_vector_bytes, ucb_score, cost):
    """
    Log a decision-time interaction.

    This represents the bandit action selection event.

    Returns:
        int: interaction_id
    """
    logger.info(
        f"Logging interaction sim={simulation_id}, customer={customer_id}, action={action_id}"
    )

    db.cursor.execute("""
        INSERT INTO public.interactions
        (simulation_id, customer_id, action_id, round_number,
         context_vector, ucb_score, cost)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING interaction_id
    """, (
        simulation_id, customer_id, action_id, round_number,
        context_vector_bytes, ucb_score, cost
    ))

    iid = db.cursor.fetchone()[0]
    db.commit()

    logger.success(f"Interaction logged id={iid}")
    return iid


def observe_outcome(db: SQLHandler, interaction_id,
                    converted: bool, revenue: float,
                    converted_at, observed_at):
    """
    Update interaction after outcome observation.

    Computes reward = revenue - cost in SQL.

    Args:
        interaction_id (int)
        converted (bool)
        revenue (float)
        converted_at (timestamp)
        observed_at (timestamp)
    """
    logger.info(f"Updating outcome for interaction_id={interaction_id}")

    db.cursor.execute("""
        UPDATE public.interactions
        SET converted = %s,
            revenue = %s,
            converted_at = %s,
            observed_at = %s,
            reward = %s - cost
        WHERE interaction_id = %s
    """, (
        converted, revenue, converted_at, observed_at,
        revenue, interaction_id
    ))

    db.commit()
    logger.success("Outcome updated")


def get_pending_interactions(db: SQLHandler, older_than_hours=48):
    """
    Fetch interactions that have not been observed yet.

    Used by outcome observer job.

    Returns:
        DataFrame
    """
    logger.info(f"Fetching pending interactions older than {older_than_hours}h")

    return db.select("""
        SELECT *
        FROM public.interactions
        WHERE observed_at IS NULL
        AND decision_at < NOW() - (%s * INTERVAL '1 hour')
    """, (older_than_hours,))


def get_model_state(db: SQLHandler, simulation_id: int, action_id: int):
    """
    Fetch latest model state for a given (simulation, action).

    Returns:
        dict | None
    """
    logger.info(f"Fetching model state sim={simulation_id}, action={action_id}")

    df = db.select("""
        SELECT *
        FROM public.model_state
        WHERE simulation_id = %s AND action_id = %s
        ORDER BY round_number DESC
        LIMIT 1
    """, (simulation_id, action_id))

    return df.iloc[0].to_dict() if not df.empty else None


def upsert_model_state(db: SQLHandler, simulation_id, action_id,
                       round_number, n_pulls,
                       theta_bytes, a_bytes, b_bytes, alpha):
    """
    Insert or update LinUCB model state snapshot.
    """
    logger.info(f"Upserting model state sim={simulation_id}, action={action_id}")

    db.cursor.execute("""
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
    """, (
        simulation_id, action_id, round_number, n_pulls,
        theta_bytes, a_bytes, b_bytes, alpha
    ))

    db.commit()
    logger.success("Model state updated")


def create_simulation(db: SQLHandler, sim_name, num_rounds,
                      num_customers, alpha,
                      context_dim=6,
                      conversion_window_hours=48,
                      notes=None):
    """
    Create a new simulation run.

    Returns:
        int: simulation_id
    """
    logger.info(f"Creating simulation {sim_name}")

    db.cursor.execute("""
        INSERT INTO public.simulations
        (sim_name, num_rounds, num_customers, alpha,
         context_dim, conversion_window_hours, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING simulation_id
    """, (
        sim_name, num_rounds, num_customers, alpha,
        context_dim, conversion_window_hours, notes
    ))

    sid = db.cursor.fetchone()[0]
    db.commit()

    logger.success(f"Simulation created id={sid}")
    return sid


def complete_simulation(db: SQLHandler, simulation_id: int):
    """
    Mark simulation as completed.
    """
    logger.info(f"Completing simulation id={simulation_id}")

    db.cursor.execute("""
        UPDATE public.simulations
        SET completed_at = NOW()
        WHERE simulation_id = %s
    """, (simulation_id,))

    db.commit()
    logger.success("Simulation completed")