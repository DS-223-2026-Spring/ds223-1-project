"""
bandit_utils.py — shared logic, theming, mock data, and API client.

Owner: Armine Babajanyan (frontend branch)

Following the instructor's convention (one flat utilities file), this module
bundles everything shared across pages:

  - Theme constants (colors, labels, costs)
  - Mock data generators (M2 only)
  - API client wrappers with USE_MOCKS toggle

When M3 lands, flip USE_MOCKS = False and implement the real `requests` calls.
Response shapes of every mock match the backend contract in docs/frontend.md.
"""
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

# ═════════════════════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════════════════════
API_BASE = os.getenv("API_URL", "http://api:8000")

# M2 kill-switch. Set to False in M3.
USE_MOCKS = True

RNG = np.random.default_rng(42)


# ═════════════════════════════════════════════════════════════
# Theme — action constants + formatters
# ═════════════════════════════════════════════════════════════
ACTION_COLORS = {
    "no_action":     "#6B7280",  # grey
    "discount_10":   "#EF4444",  # red
    "free_shipping": "#3B82F6",  # blue
    "product_rec":   "#10B981",  # emerald
    "bundle_offer":  "#F59E0B",  # amber
}

ACTION_LABELS = {
    "no_action":     "No action",
    "discount_10":   "10% discount",
    "free_shipping": "Free shipping",
    "product_rec":   "Product recommendation",
    "bundle_offer":  "Bundle offer",
}

ACTION_COSTS = {
    "no_action":     0.00,
    "discount_10":   6.50,
    "free_shipping": 4.99,
    "product_rec":   0.30,
    "bundle_offer":  9.00,
}

RFM_FEATURES = [
    "recency",
    "frequency",
    "monetary",
    "basket_diversity",
    "avg_order_size",
    "purchase_regularity",
]


def format_currency(value):
    if value is None or pd.isna(value):
        return "—"
    return f"£{value:,.2f}"


def format_pct(value):
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:.1f}%"


# ═════════════════════════════════════════════════════════════
# Mock data generators (M2 only — remove in M3)
# ═════════════════════════════════════════════════════════════
def _mock_simulations(n: int = 4) -> pd.DataFrame:
    rows = []
    for i in range(n):
        started = datetime.now() - timedelta(
            days=n - i, hours=int(RNG.integers(0, 12))
        )
        is_running = i == n - 1
        completed = None if is_running else started + timedelta(
            hours=int(RNG.integers(1, 8))
        )
        rows.append({
            "simulation_id": i + 1,
            "sim_name": f"run_{i+1:03d}",
            "num_rounds": int(RNG.choice([1000, 2500, 5000])),
            "num_customers": 500,
            "alpha": float(RNG.choice([0.1, 0.3, 0.5])),
            "started_at": started,
            "completed_at": completed,
            "status": "running" if is_running else "completed",
            "cumulative_reward": None if is_running else float(
                RNG.uniform(2000, 8000)
            ),
        })
    return pd.DataFrame(rows)


def _mock_cumulative_reward(n_rounds: int = 1000) -> pd.DataFrame:
    rounds = np.arange(1, n_rounds + 1)
    return pd.DataFrame({
        "round":     rounds,
        "linucb":    np.cumsum(RNG.normal(3.5, 2.0, n_rounds)),
        "heuristic": np.cumsum(RNG.normal(2.5, 2.0, n_rounds)),
        "random":    np.cumsum(RNG.normal(1.5, 2.0, n_rounds)),
    })


def _mock_action_distribution(n_rounds: int = 1000) -> pd.DataFrame:
    """Exploration narrowing into exploitation."""
    actions = list(ACTION_LABELS.keys())
    data = []
    for r in range(1, n_rounds + 1):
        phase = min(r / n_rounds, 1.0)
        start_w = np.ones(5) * 0.20
        end_w = np.array([0.10, 0.35, 0.15, 0.25, 0.15])
        weights = start_w * (1 - phase) + end_w * phase
        weights /= weights.sum()
        data.append({"round": r, "action": RNG.choice(actions, p=weights)})
    return pd.DataFrame(data)


def _mock_conversion_by_action() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "action": k,
            "conversion_rate": float(RNG.uniform(0.05, 0.35)),
            "n_pulls": int(RNG.integers(100, 500)),
        }
        for k in ACTION_LABELS
    ])


def _mock_recent_interactions(n: int = 20) -> pd.DataFrame:
    actions = list(ACTION_LABELS.keys())
    rows = []
    for i in range(n):
        action = RNG.choice(actions)
        converted = bool(RNG.random() < 0.2)
        revenue = float(RNG.normal(65, 15)) if converted else 0.0
        cost = ACTION_COSTS[action]
        rows.append({
            "interaction_id": 10000 + i,
            "customer_id": int(RNG.integers(1, 500)),
            "action": action,
            "converted": converted,
            "revenue": revenue,
            "reward": revenue - cost,
            "decision_at": datetime.now() - timedelta(
                minutes=int(RNG.integers(1, 180))
            ),
        })
    return pd.DataFrame(rows)


def _mock_customers(n: int = 200) -> pd.DataFrame:
    segments = ["Champion", "Loyal", "At Risk", "Lost", "New"]
    genders = ["F", "M"]
    rows = []
    for i in range(n):
        rows.append({
            "customer_id": i + 1,
            "segment_label": str(RNG.choice(segments)),
            "gender": str(RNG.choice(genders)),
            "recency": float(RNG.exponential(20)),
            "frequency": float(RNG.poisson(8)),
            "monetary": float(max(50, RNG.normal(450, 150))),
            "basket_diversity": float(RNG.uniform(1, 8)),
            "avg_order_size": float(max(1, RNG.normal(3, 1))),
            "purchase_regularity": float(RNG.uniform(0, 30)),
        })
    return pd.DataFrame(rows)


def _mock_theta_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        RNG.normal(0, 0.5, (6, 5)),
        index=RFM_FEATURES,
        columns=list(ACTION_LABELS.keys()),
    )


def _mock_ucb_breakdown(customer_id: int) -> pd.DataFrame:
    rows = []
    for a in ACTION_LABELS:
        exploit = float(RNG.uniform(-1, 5))
        explore = float(RNG.uniform(0, 2))
        rows.append({
            "action": a,
            "exploit": exploit,
            "explore": explore,
            "ucb_score": exploit + explore,
            "cost": ACTION_COSTS[a],
        })
    return pd.DataFrame(rows).sort_values("ucb_score", ascending=False)


# ═════════════════════════════════════════════════════════════
# API client — all HTTP calls go through here
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=10)
def list_simulations():
    """GET /simulations → DataFrame of all simulation runs."""
    if USE_MOCKS:
        return _mock_simulations()
    # TODO M3:
    # import requests
    # return pd.DataFrame(requests.get(f"{API_BASE}/simulations").json())
    raise NotImplementedError


def create_simulation(sim_name: str, num_rounds: int, num_customers: int,
                      alpha: float, notes: str = "") -> dict:
    """POST /simulate → trigger a new run, returns {simulation_id, status}."""
    if USE_MOCKS:
        return {
            "simulation_id": 999,
            "status": "queued",
            "sim_name": sim_name,
        }
    raise NotImplementedError


@st.cache_data(ttl=30)
def get_metrics(simulation_id: int) -> dict:
    """GET /metrics?simulation_id=... → all dashboard aggregates."""
    if USE_MOCKS:
        return {
            "rounds_completed": 847,
            "cumulative_reward": 3214.55,
            "avg_reward_per_round": 3.79,
            "pending_observations": 22,
            "cumulative_reward_series": _mock_cumulative_reward(),
            "action_distribution": _mock_action_distribution(),
            "conversion_by_action": _mock_conversion_by_action(),
            "recent_interactions": _mock_recent_interactions(),
        }
    raise NotImplementedError


@st.cache_data(ttl=60)
def list_customers():
    """GET /customers → DataFrame with RFM features."""
    if USE_MOCKS:
        return _mock_customers(n=200)
    raise NotImplementedError


@st.cache_data(ttl=60)
def get_customer(customer_id: int) -> dict:
    """GET /customers/{id} → one customer profile + interactions + latents."""
    if USE_MOCKS:
        df = _mock_customers(n=1)
        return df.iloc[0].to_dict()
    raise NotImplementedError


@st.cache_data(ttl=30)
def get_model_state(simulation_id: int) -> dict:
    """GET /model/state?simulation_id=... → θ, n_pulls, alpha."""
    if USE_MOCKS:
        conv = _mock_conversion_by_action()
        return {
            "theta": _mock_theta_matrix(),
            "n_pulls": dict(zip(conv["action"], conv["n_pulls"])),
            "alpha": 0.5,
        }
    raise NotImplementedError


def predict_for_customer(customer_id: int):
    """POST /decide?customer_id=...&preview=true → per-action UCB breakdown."""
    if USE_MOCKS:
        return _mock_ucb_breakdown(customer_id)
    raise NotImplementedError


# ═════════════════════════════════════════════════════════════
# UI helpers — shared widget builders (instructor-style)
# ═════════════════════════════════════════════════════════════
def select_simulation_widget(key: str = "sim_select"):
    """
    Dropdown that picks a simulation. Respects st.session_state
    for cross-page consistency.
    """
    sims = list_simulations()
    if sims.empty:
        return None, sims

    default_sim = st.session_state.get(
        "selected_simulation_id", int(sims["simulation_id"].max())
    )
    sim_id = st.selectbox(
        "Simulation",
        options=sims["simulation_id"].tolist(),
        index=sims["simulation_id"].tolist().index(default_sim),
        format_func=lambda x: (
            f"#{x} · {sims.loc[sims.simulation_id == x, 'sim_name'].iloc[0]}"
        ),
        key=key,
    )
    st.session_state["selected_simulation_id"] = sim_id
    return sim_id, sims
