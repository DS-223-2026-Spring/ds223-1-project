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
    logger.info("Fetching all customers")
    return db.select("SELECT * FROM public.customers")


def get_customer_by_id(db: SQLHandler, customer_id: int):
    logger.info(f"Fetching customer_id={customer_id}")
    df = db.select(
        "SELECT * FROM public.customers WHERE customer_id = %s",
        (customer_id,),
    )
    return df.iloc[0].to_dict() if not df.empty else None


def get_customer_latents(db: SQLHandler, customer_id: int):
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
    logger.info("Inserting new customer")
    db.cursor.execute(
        """
        INSERT INTO public.customers
        (gender, segment_label, recency, frequency, monetary,
         basket_diversity, avg_order_size, purchase_regularity)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING customer_id
        """,
        (
            gender,
            segment_label,
            recency,
            frequency,
            monetary,
            basket_diversity,
            avg_order_size,
            purchase_regularity,
        ),
    )

    customer_id = db.cursor.fetchone()[0]
    db.commit()
    logger.success(f"Inserted customer_id={customer_id}")
    return customer_id


def insert_customer_latent(
    db: SQLHandler,
    customer_id,
    z_price_sensitivity,
    z_brand_loyalty,
    z_impulse_tendency,
):
    logger.info(f"Inserting latents for customer_id={customer_id}")
    db.cursor.execute(
        """
        INSERT INTO public.customer_latents
        (customer_id, z_price_sensitivity, z_brand_loyalty, z_impulse_tendency)
        VALUES (%s,%s,%s,%s)
        """,
        (
            customer_id,
            z_price_sensitivity,
            z_brand_loyalty,
            z_impulse_tendency,
        ),
    )
    db.commit()
    logger.success("Latents inserted")


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
    logger.info(
        f"Logging interaction sim={simulation_id}, customer={customer_id}, action={action_id}"
    )
    db.cursor.execute(
        """
        INSERT INTO public.interactions
        (simulation_id, customer_id, action_id, round_number,
         context_vector, ucb_score, cost)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING interaction_id
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
    logger.success(f"Interaction logged id={interaction_id}")
    return interaction_id


def observe_outcome(
    db: SQLHandler,
    interaction_id,
    converted: bool,
    revenue: float,
    converted_at,
    observed_at,
):
    logger.info(f"Updating outcome for interaction_id={interaction_id}")
    db.cursor.execute(
        """
        UPDATE public.interactions
        SET converted = %s,
            revenue = %s,
            converted_at = %s,
            observed_at = %s,
            reward = %s - cost
        WHERE interaction_id = %s
        """,
        (
            converted,
            revenue,
            converted_at,
            observed_at,
            revenue,
            interaction_id,
        ),
    )
    db.commit()
    logger.success("Outcome updated")


def get_pending_interactions(db: SQLHandler, older_than_hours=48):
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
