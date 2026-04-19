"""
Orchestration — Prefect Flows
Owner: Orchestration role (shared, coordinated by Anna)

PURPOSE:
  Prefect transforms the bandit from a one-shot script into a
  continuously running real-time system.

  The key architectural insight:
    Decision and outcome are SEPARATED IN TIME.
    Flow 2 assigns actions (decision_at = now).
    Flow 3 observes outcomes after conversion_window_hours elapse.
    This gap is what makes the system feel like a live campaign system,
    not a batch simulation.

  Prefect manages this gap. The Streamlit dashboard shows both
  completed interactions (reward known) and pending ones (awaiting outcome).

Flow map:
  Flow 1: generate_customers     — runs ONCE at simulation start
  Flow 2: decision_loop          — scheduled, assigns actions to customers
  Flow 3: outcome_observer       — scheduled, closes pending interactions
  Flow 4: model_update           — triggered by Flow 3 after outcomes observed
  Flow 5: metrics_refresh        — scheduled, caches dashboard metrics

Tasks (#60–#67):
  M2: Set up Prefect server, verify flows run locally
  M2: Define Flow 1 and Flow 2 (decision side)
  M3: Implement Flow 3 + Flow 4 (outcome + model update)
  M3: Schedule flows with Prefect deployments
  M3: Add Flow 5 for dashboard refresh
  M4: Add alerting if cumulative reward drops
"""

import os
from datetime import timedelta

# from prefect import flow, task
# from prefect.schedules import IntervalSchedule

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "db"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("POSTGRES_DB", "campaign"),
    "user":     os.getenv("POSTGRES_USER", "campaign_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "campaign_pass"),
}

PREFECT_API_URL          = os.getenv("PREFECT_API_URL", "http://prefect:4200/api")
CONVERSION_WINDOW_HOURS  = int(os.getenv("CONVERSION_WINDOW_HOURS", 48))
DECISION_BATCH_SIZE      = int(os.getenv("DECISION_BATCH_SIZE", 20))


# ── Flow 1: Customer Generation ───────────────────────────────────────────────
# @flow(name="generate-customers", description="Run once — populates customers + customer_latents")
def generate_customers_flow(n_customers: int = 500, seed: int = 42):
    """
    Triggers ETL service to generate customers with latent traits.
    Runs ONCE before any simulation starts.
    Idempotent: checks if customers already exist before generating.

    TODO (Orchestration M2): implement
    """
    print(f"[Flow 1] Generating {n_customers} customers...")
    # TODO: call ETL main() or trigger via subprocess
    # TODO: verify customer_latents populated (same count as customers)
    raise NotImplementedError


# ── Flow 2: Decision Loop ──────────────────────────────────────────────────────
# @flow(name="decision-loop", description="Assign actions to a batch of customers")
def decision_loop_flow(simulation_id: int, batch_size: int = DECISION_BATCH_SIZE):
    """
    Runs on schedule (e.g., every 2 minutes in fast-sim mode).
    For each customer in batch:
      - Load context vector x from customers table
      - Call LinUCB → select action
      - Write interaction row: decision_at=now(), observed_at=NULL
    Pending interactions are visible in Streamlit dashboard.

    TODO (Orchestration M3): implement
    """
    print(f"[Flow 2] Running decision batch for simulation {simulation_id}...")
    raise NotImplementedError


# ── Flow 3: Outcome Observer ───────────────────────────────────────────────────
# @flow(name="observe-outcomes", description="Close pending interactions past conversion window")
def observe_outcomes_flow():
    """
    Runs on schedule (e.g., every 5 minutes).
    Finds interactions WHERE:
      observed_at IS NULL
      AND decision_at < now() - interval 'CONVERSION_WINDOW_HOURS hours'

    For each pending interaction:
      1. Load customer_latents for that customer_id
      2. Call p_convert(latents, action_name) → Bernoulli draw
      3. Set converted_at, observed_at, revenue, reward
      4. Trigger model_update_flow

    This is where the conversion_window matters — interactions stay
    'pending' for CONVERSION_WINDOW_HOURS before outcome is revealed.

    TODO (Orchestration M3): implement
    """
    print("[Flow 3] Observing pending interactions...")
    raise NotImplementedError


# ── Flow 4: Model Update ───────────────────────────────────────────────────────
# @flow(name="model-update", description="Update LinUCB parameters after observing outcomes")
def model_update_flow(interaction_ids: list):
    """
    Triggered by Flow 3 after outcomes are set.
    For each newly observed interaction:
      1. Load context_vector (bytea) and reward from interactions table
      2. Update LinUCB: A += xxᵀ, b += r*x, θ = A⁻¹b
      3. Write updated model_state (theta, A, b, n_pulls, round_number)

    Uses in-memory agent state — persistence is via model_state table.
    On restart: reconstruct agent from latest model_state rows.

    TODO (Orchestration M3): implement
    """
    print(f"[Flow 4] Updating model for {len(interaction_ids)} new outcomes...")
    raise NotImplementedError


# ── Flow 5: Metrics Refresh ───────────────────────────────────────────────────
# @flow(name="refresh-metrics", description="Compute and cache dashboard metrics")
def refresh_metrics_flow(simulation_id: int):
    """
    Runs on schedule (e.g., every 5 minutes).
    Aggregates from interactions table:
      - cumulative reward
      - action distribution (count per action)
      - conversion rate per action
      - pending observation count
    Writes to a metrics cache table or returns via API.

    TODO (Orchestration M4): implement
    """
    print(f"[Flow 5] Refreshing metrics for simulation {simulation_id}...")
    raise NotImplementedError


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Prefect flows registered. Deploy with:")
    print("  prefect deployment build flows.py:generate_customers_flow -n dev")
    print("  prefect deployment apply generate_customers_flow-deployment.yaml")
    print("  prefect agent start -q default")
    print(f"  Prefect UI: {PREFECT_API_URL.replace('/api','')}")
