"""
Database CRUD helpers — Campaign Optimization Engine
Owner: Hayk Alekyan (db branch)

These helpers are used by the model service (Davit) and the API (Victoria).
All DB access outside of this file should be avoided — use these methods.

Tasks (#29, #30):
  - Implement all functions below
  - Add clear docstrings to each
  - Verify with: python crud.py (runs smoke test at bottom)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "db"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("POSTGRES_DB", "campaign"),
    "user":     os.getenv("POSTGRES_USER", "campaign_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "campaign_pass"),
}


def get_connection():
    """Return a new psycopg2 connection."""
    return psycopg2.connect(**DB_CONFIG)


# ── CUSTOMERS ────────────────────────────────────────────────────────────────

def get_all_customers():
    """Return list of all customers as dicts."""
    # TODO (Hayk): implement
    raise NotImplementedError


def get_customer_by_id(customer_id: int):
    """Return one customer dict or None."""
    # TODO (Hayk): implement
    raise NotImplementedError


def get_customer_latents(customer_id: int):
    """Return latent traits dict for a customer (debug / simulation use only)."""
    # TODO (Hayk): implement
    raise NotImplementedError


def insert_customer(gender, segment_label, recency, frequency, monetary,
                    basket_diversity, avg_order_size, purchase_regularity):
    """Insert one customer row, return customer_id."""
    # TODO (Hayk): implement
    raise NotImplementedError


def insert_customer_latent(customer_id, z_price_sensitivity,
                            z_brand_loyalty, z_impulse_tendency):
    """Insert latent traits for a customer."""
    # TODO (Hayk): implement
    raise NotImplementedError


# ── INTERACTIONS ─────────────────────────────────────────────────────────────

def log_interaction(simulation_id, customer_id, action_id, round_number,
                    context_vector_bytes, ucb_score, cost):
    """
    Insert a new interaction at decision time.
    converted, revenue, reward, converted_at, observed_at are all NULL — set later by observe_outcome.
    Return interaction_id.
    """
    # TODO (Hayk): implement
    raise NotImplementedError


def observe_outcome(interaction_id, converted: bool, revenue: float,
                    converted_at, observed_at):
    """
    Set outcome fields on an existing interaction after conversion window elapses.
    Computes reward = revenue - cost.
    """
    # TODO (Hayk): implement
    raise NotImplementedError


def get_pending_interactions(older_than_hours: int = 48):
    """
    Return interactions where observed_at IS NULL and
    decision_at < now() - interval.
    Used by Prefect outcome_observer flow.
    """
    # TODO (Hayk): implement
    raise NotImplementedError


# ── MODEL STATE ───────────────────────────────────────────────────────────────

def get_model_state(simulation_id: int, action_id: int):
    """Return latest model_state row for this simulation + action."""
    # TODO (Hayk): implement
    raise NotImplementedError


def upsert_model_state(simulation_id, action_id, round_number, n_pulls,
                       theta_bytes, a_bytes, b_bytes, alpha):
    """Insert or update model state after a LinUCB update step."""
    # TODO (Hayk): implement
    raise NotImplementedError


# ── SIMULATIONS ───────────────────────────────────────────────────────────────

def create_simulation(sim_name, num_rounds, num_customers, alpha,
                      context_dim=6, conversion_window_hours=48, notes=None):
    """Insert a new simulation record, return simulation_id."""
    # TODO (Hayk): implement
    raise NotImplementedError


def complete_simulation(simulation_id: int):
    """Set completed_at = now() on a simulation."""
    # TODO (Hayk): implement
    raise NotImplementedError


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
