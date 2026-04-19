"""
Database CRUD helpers — Campaign Optimization Engine
Owner: Hayk Alekyan (db branch)

These helpers are used by the model service (Davit) and the API (Victoria).
All DB access outside of this file should be avoided — use these methods.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB", "campaign"),
    "user": os.getenv("POSTGRES_USER", "campaign_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "campaign_pass"),
}


def get_connection():
    """Return a new psycopg2 connection."""

    return psycopg2.connect(**DB_CONFIG)


def _fetchall(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    """Run a SELECT query and return all rows as plain dicts."""

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def _fetchone(query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
    """Run a SELECT query and return one row as a plain dict."""

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row is not None else None


def _execute_returning_id(query: str, params: tuple[Any, ...]) -> int:
    """Run a write query that returns a single integer id."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            conn.commit()
            if row is None:
                raise RuntimeError("Expected RETURNING id row but query returned nothing")
            return int(row[0])


def _execute(query: str, params: tuple[Any, ...] | None = None) -> None:
    """Run a write query without returning rows."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()


# ── CUSTOMERS ────────────────────────────────────────────────────────────────

def get_all_customers():
    """Return all customers ordered by customer_id."""

    return _fetchall(
        """
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
            created_at
        FROM customers
        ORDER BY customer_id;
        """
    )


def get_customer_by_id(customer_id: int):
    """Return one customer dict or None."""

    return _fetchone(
        """
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
            created_at
        FROM customers
        WHERE customer_id = %s;
        """,
        (customer_id,),
    )


def get_customer_latents(customer_id: int):
    """Return latent traits dict for a customer."""

    return _fetchone(
        """
        SELECT
            customer_id,
            z_price_sensitivity,
            z_brand_loyalty,
            z_impulse_tendency,
            created_at
        FROM customer_latents
        WHERE customer_id = %s;
        """,
        (customer_id,),
    )


def insert_customer(
    gender,
    segment_label,
    recency,
    frequency,
    monetary,
    basket_diversity,
    avg_order_size,
    purchase_regularity,
):
    """Insert one customer row and return customer_id."""

    return _execute_returning_id(
        """
        INSERT INTO customers (
            gender,
            segment_label,
            recency,
            frequency,
            monetary,
            basket_diversity,
            avg_order_size,
            purchase_regularity
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING customer_id;
        """,
        (
            gender,
            segment_label,
            int(recency),
            int(frequency),
            float(monetary),
            float(basket_diversity),
            float(avg_order_size),
            float(purchase_regularity),
        ),
    )


def insert_customer_latent(
    customer_id,
    z_price_sensitivity,
    z_brand_loyalty,
    z_impulse_tendency,
):
    """Insert or replace latent traits for a customer."""

    _execute(
        """
        INSERT INTO customer_latents (
            customer_id,
            z_price_sensitivity,
            z_brand_loyalty,
            z_impulse_tendency
        ) VALUES (%s, %s, %s, %s)
        ON CONFLICT (customer_id) DO UPDATE SET
            z_price_sensitivity = EXCLUDED.z_price_sensitivity,
            z_brand_loyalty = EXCLUDED.z_brand_loyalty,
            z_impulse_tendency = EXCLUDED.z_impulse_tendency;
        """,
        (
            int(customer_id),
            float(z_price_sensitivity),
            float(z_brand_loyalty),
            float(z_impulse_tendency),
        ),
    )


# ── INTERACTIONS ─────────────────────────────────────────────────────────────

def log_interaction(
    simulation_id,
    customer_id,
    action_id,
    round_number,
    context_vector_bytes,
    ucb_score,
    cost,
):
    """
    Insert a new interaction at decision time and return interaction_id.
    """

    return _execute_returning_id(
        """
        INSERT INTO interactions (
            simulation_id,
            customer_id,
            action_id,
            round_number,
            context_vector,
            ucb_score,
            cost
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING interaction_id;
        """,
        (
            int(simulation_id),
            int(customer_id),
            int(action_id),
            int(round_number),
            context_vector_bytes,
            None if ucb_score is None else float(ucb_score),
            float(cost),
        ),
    )


def observe_outcome(interaction_id, converted: bool, revenue: float, converted_at, observed_at):
    """
    Set outcome fields on an existing interaction after the conversion window elapses.
    Computes reward = revenue - cost.
    """

    row = _fetchone(
        "SELECT cost FROM interactions WHERE interaction_id = %s;",
        (interaction_id,),
    )
    if row is None:
        raise ValueError(f"interaction_id {interaction_id} does not exist")

    revenue_value = float(revenue)
    cost_value = float(row["cost"])
    reward_value = revenue_value - cost_value

    _execute(
        """
        UPDATE interactions
        SET
            converted = %s,
            revenue = %s,
            reward = %s,
            converted_at = %s,
            observed_at = %s
        WHERE interaction_id = %s;
        """,
        (
            bool(converted),
            revenue_value,
            reward_value,
            converted_at,
            observed_at,
            int(interaction_id),
        ),
    )


def get_pending_interactions(older_than_hours: int = 48):
    """Return pending interactions whose conversion window has elapsed."""

    return _fetchall(
        """
        SELECT
            interaction_id,
            simulation_id,
            customer_id,
            action_id,
            round_number,
            context_vector,
            ucb_score,
            cost,
            converted,
            revenue,
            reward,
            decision_at,
            converted_at,
            observed_at
        FROM interactions
        WHERE observed_at IS NULL
          AND decision_at < NOW() - (%s * INTERVAL '1 hour')
        ORDER BY decision_at ASC;
        """,
        (int(older_than_hours),),
    )


# ── MODEL STATE ───────────────────────────────────────────────────────────────

def get_model_state(simulation_id: int, action_id: int):
    """Return latest model_state row for this simulation + action."""

    return _fetchone(
        """
        SELECT
            model_state_id,
            simulation_id,
            action_id,
            round_number,
            n_pulls,
            theta_bytes,
            a_bytes,
            b_bytes,
            alpha,
            updated_at
        FROM model_state
        WHERE simulation_id = %s
          AND action_id = %s;
        """,
        (int(simulation_id), int(action_id)),
    )


def upsert_model_state(
    simulation_id,
    action_id,
    round_number,
    n_pulls,
    theta_bytes,
    a_bytes,
    b_bytes,
    alpha,
):
    """Insert or update model state after a LinUCB update step."""

    _execute(
        """
        INSERT INTO model_state (
            simulation_id,
            action_id,
            round_number,
            n_pulls,
            theta_bytes,
            a_bytes,
            b_bytes,
            alpha
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (simulation_id, action_id) DO UPDATE SET
            round_number = EXCLUDED.round_number,
            n_pulls = EXCLUDED.n_pulls,
            theta_bytes = EXCLUDED.theta_bytes,
            a_bytes = EXCLUDED.a_bytes,
            b_bytes = EXCLUDED.b_bytes,
            alpha = EXCLUDED.alpha,
            updated_at = CURRENT_TIMESTAMP;
        """,
        (
            int(simulation_id),
            int(action_id),
            int(round_number),
            int(n_pulls),
            theta_bytes,
            a_bytes,
            b_bytes,
            float(alpha),
        ),
    )


# ── SIMULATIONS ───────────────────────────────────────────────────────────────

def create_simulation(
    sim_name,
    num_rounds,
    num_customers,
    alpha,
    context_dim=6,
    conversion_window_hours=48,
    notes=None,
):
    """Insert a new simulation record and return simulation_id."""

    return _execute_returning_id(
        """
        INSERT INTO simulations (
            sim_name,
            num_rounds,
            num_customers,
            alpha,
            context_dim,
            conversion_window_hours,
            notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING simulation_id;
        """,
        (
            sim_name,
            int(num_rounds),
            int(num_customers),
            float(alpha),
            int(context_dim),
            int(conversion_window_hours),
            notes,
        ),
    )


def complete_simulation(simulation_id: int):
    """Set completed_at = now() on a simulation."""

    _execute(
        """
        UPDATE simulations
        SET completed_at = CURRENT_TIMESTAMP
        WHERE simulation_id = %s;
        """,
        (int(simulation_id),),
    )


# ── SMOKE TEST ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT COUNT(*) AS n FROM customers;")
    print("customers:", cur.fetchone())
    cur.execute("SELECT action_name, action_cost FROM actions ORDER BY action_id;")
    for row in cur.fetchall():
        print(row)
    conn.close()
    print("DB connection OK")
