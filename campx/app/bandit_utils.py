"""
bandit_utils.py — shared API client, theme constants, and formatters.

Owner: Armine Babajanyan (frontend branch)

M3: Fully wired to the FastAPI backend. No mock generators, no Plotly.
All HTTP calls go through this module so pages stay thin.

Only built-in Streamlit components and pandas/numpy are used downstream.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ═════════════════════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════════════════════
API_BASE = os.getenv("API_URL", "http://backend:8000").rstrip("/")
HTTP_TIMEOUT = float(os.getenv("API_TIMEOUT_SECONDS", "10"))


# ═════════════════════════════════════════════════════════════
# Theme — action constants + formatters
# ═════════════════════════════════════════════════════════════
ACTION_COLORS = {
    "no_action":              "#6B7280",  # grey
    "discount_10":            "#EF4444",  # red
    "free_shipping":          "#3B82F6",  # blue
    "product_recommendation": "#10B981",  # emerald
    "bundle_offer":           "#F59E0B",  # amber
}

ACTION_LABELS = {
    "no_action":              "No action",
    "discount_10":            "10% off",
    "free_shipping":          "Free ship.",
    "product_recommendation": "Product rec.",
    "bundle_offer":           "Bundle",
}

ACTION_COSTS = {
    "no_action":              0.00,
    "discount_10":            6.50,
    "free_shipping":          4.99,
    "product_recommendation": 0.30,
    "bundle_offer":           9.00,
}

RFM_FEATURES = [
    "recency",
    "frequency",
    "monetary",
    "basket_diversity",
    "avg_order_size",
    "purchase_regularity",
]


def format_currency(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"£{value:,.2f}"


def format_pct(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"{value * 100:.1f}%"


# ═════════════════════════════════════════════════════════════
# Low-level HTTP helpers
# ═════════════════════════════════════════════════════════════
class APIError(RuntimeError):
    """Raised when the backend returns a non-2xx response or is unreachable."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _request(method: str, path: str, **kwargs) -> Any:
    """Single entry point for every backend call. Raises APIError on failure."""
    url = f"{API_BASE}{path}"
    try:
        resp = requests.request(method, url, timeout=HTTP_TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise APIError(f"Could not reach backend at {url}: {exc}") from exc

    if not resp.ok:
        # Try to surface the structured error from the backend
        try:
            payload = resp.json()
            detail = payload.get("detail") or payload.get("message") or payload
        except ValueError:
            detail = resp.text or resp.reason
        raise APIError(f"{method} {path} → {resp.status_code}: {detail}",
                       status_code=resp.status_code)

    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def _to_datetime(series: pd.Series) -> pd.Series:
    """Parse ISO-8601 strings into pandas datetimes; pass through if already typed."""
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)


# ═════════════════════════════════════════════════════════════
# Health / status
# ═════════════════════════════════════════════════════════════
def backend_health() -> dict:
    """GET /health — used by the landing page status banner."""
    return _request("GET", "/health")


# ═════════════════════════════════════════════════════════════
# Simulations
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=10, show_spinner=False)
def list_simulations() -> pd.DataFrame:
    """GET /simulations → DataFrame of every run, newest first."""
    payload = _request("GET", "/simulations")
    if not payload:
        return pd.DataFrame(columns=[
            "simulation_id", "sim_name", "num_rounds", "num_customers",
            "alpha", "started_at", "completed_at", "status",
            "cumulative_reward",
        ])
    df = pd.DataFrame(payload)
    if "started_at" in df.columns:
        df["started_at"] = _to_datetime(df["started_at"])
    if "completed_at" in df.columns:
        df["completed_at"] = _to_datetime(df["completed_at"])
    return df


def create_simulation(sim_name: str, num_rounds: float, num_customers: float,
                      alpha: float, notes: str = "") -> dict:
    """POST /simulations — returns the created simulation record."""
    body = {
        "sim_name": sim_name,
        "num_rounds": int(num_rounds),
        "num_customers": int(num_customers),
        "alpha": float(alpha),
        "notes": notes or None,
    }
    return _request("POST", "/simulations", json=body)


# ═════════════════════════════════════════════════════════════
# Metrics — partial backend support, normalised here
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=15, show_spinner=False)
def get_metrics(simulation_id: int) -> dict:
    """
    GET /metrics?simulation_id=...

    Backend currently returns the lightweight shape:
      {simulation_id, total_interactions, conversions,
       total_revenue, total_cost, total_reward}

    The Interaction/Analytics pages also expect:
      rounds_completed, cumulative_reward, avg_reward_per_round,
      pending_observations, cumulative_reward_series (DataFrame),
      action_distribution (DataFrame), conversion_by_action (DataFrame),
      recent_interactions (DataFrame).

    This function fills in what it can and returns sentinel `None` /
    empty DataFrames for fields the backend has not implemented yet.
    The pages render gracefully around missing pieces.
    """
    raw = _request("GET", "/metrics", params={"simulation_id": simulation_id})
    if raw is None:
        raw = {}

    total_interactions = int(raw.get("total_interactions", 0) or 0)
    total_reward = float(raw.get("total_reward", 0.0) or 0.0)

    # Synthesised KPI fields (cheap, safe to compute here)
    avg_reward = (total_reward / total_interactions) if total_interactions else 0.0

    # Pass through richer fields if/when the backend starts emitting them.
    cum_series = pd.DataFrame(raw.get("cumulative_reward_series") or [])
    action_dist = pd.DataFrame(raw.get("action_distribution") or [])
    conv_by_action = pd.DataFrame(raw.get("conversion_by_action") or [])
    recent = pd.DataFrame(raw.get("recent_interactions") or [])
    if not recent.empty and "decision_at" in recent.columns:
        recent["decision_at"] = _to_datetime(recent["decision_at"])

    return {
        "simulation_id": raw.get("simulation_id", simulation_id),
        "status": raw.get("status"),
        "rounds_completed": raw.get("rounds_completed", total_interactions),
        "cumulative_reward": raw.get("cumulative_reward", total_reward),
        "avg_reward_per_round": raw.get("avg_reward_per_round", avg_reward),
        "pending_observations": raw.get("pending_observations"),
        "total_revenue": float(raw.get("total_revenue", 0.0) or 0.0),
        "total_cost": float(raw.get("total_cost", 0.0) or 0.0),
        "conversions": int(raw.get("conversions", 0) or 0),
        # Optional richer arrays — empty for now, will populate when backend ships
        "cumulative_reward_series": cum_series,
        "action_distribution": action_dist,
        "conversion_by_action": conv_by_action,
        "recent_interactions": recent,
    }


# ═════════════════════════════════════════════════════════════
# Customers
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=60, show_spinner=False)
def list_customers() -> pd.DataFrame:
    """GET /customers → DataFrame with RFM features."""
    limit = 500
    offset = 0
    all_customers = []
    
    while True:
        payload = _request("GET", "/customers", params={"limit": limit, "offset": offset})
        if not payload:
            break
        all_customers.extend(payload)
        if len(payload) < limit:
            break
        offset += limit
        
    df = pd.DataFrame(all_customers)
    if df.empty:
        return df
    # Normalise dtypes for safer filtering downstream
    for col in RFM_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=30, show_spinner=False)
def get_customer(customer_id: int, debug: bool = False) -> dict:
    """GET /customers/{id} → profile + interactions (+ optional latents)."""
    params = {"debug": "true"} if debug else None
    return _request("GET", f"/customers/{int(customer_id)}", params=params)


# ═════════════════════════════════════════════════════════════
# Model state
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=15, show_spinner=False)
def get_model_state(simulation_id: int) -> dict:
    """
    GET /model/state?simulation_id=...

    Backend shape:
      {
        simulation_id: int,
        alpha: float,
        round_number: int,
        updated_at: datetime | null,
        n_pulls: {action_name: int, ...},
        theta: {action_name: {feature_name: float, ...}, ...}
      }

    Returned shape (for page convenience):
      {alpha, round_number, updated_at, n_pulls (dict),
       theta (DataFrame indexed by feature, cols by action)}
    """
    raw = _request("GET", "/model/state", params={"simulation_id": simulation_id})
    n_pulls = dict(raw.get("n_pulls") or {})
    # Ensure every action shows up even when never pulled
    for action_name in ACTION_LABELS:
        n_pulls.setdefault(action_name, 0)

    theta_raw = raw.get("theta") or {}
    if theta_raw:
        # Backend shape: theta[feature_name][action_name] -> float
        # Use orient='index' so outer keys (features) become rows, inner
        # keys (actions) become columns.
        theta_df = pd.DataFrame.from_dict(theta_raw, orient="index").reindex(
            index=RFM_FEATURES
        )
    else:
        theta_df = pd.DataFrame(
            np.zeros((len(RFM_FEATURES), len(ACTION_LABELS))),
            index=RFM_FEATURES,
            columns=list(ACTION_LABELS.keys()),
        )
    # Ensure column order matches ACTION_LABELS for stable rendering
    theta_df = theta_df.reindex(columns=list(ACTION_LABELS.keys()), fill_value=0.0)

    return {
        "alpha": float(raw.get("alpha", 0.0) or 0.0),
        "round_number": int(raw.get("round_number", 0) or 0),
        "updated_at": raw.get("updated_at"),
        "n_pulls": n_pulls,
        "theta": theta_df,
    }


def predict_for_customer(simulation_id: int, customer_id: int) -> pd.DataFrame:
    """POST /decide?preview=true — per-action UCB breakdown for one customer."""
    payload = _request(
        "POST",
        "/decide",
        params={
            "simulation_id": int(simulation_id),
            "customer_id": int(customer_id),
            "preview": "true",
        },
    )
    df = pd.DataFrame(payload or [])
    if df.empty:
        return df
    # Sort best-action-first (defensive — backend already does this)
    return df.sort_values("ucb_score", ascending=False).reset_index(drop=True)


# ═════════════════════════════════════════════════════════════
# Shared widgets
# ═════════════════════════════════════════════════════════════
def select_simulation_widget(key: str = "sim_select"):
    """
    Sidebar/page selector that picks a simulation. Persists choice in
    st.session_state so navigating between pages keeps the same run selected.
    """
    try:
        sims = list_simulations()
    except APIError as exc:
        st.error(f"Could not load simulations: {exc}")
        return None, pd.DataFrame()

    if sims.empty:
        return None, sims

    options = sims["simulation_id"].tolist()
    default_sim = st.session_state.get("selected_simulation_id", options[0])
    if default_sim not in options:
        default_sim = options[0]

    sim_id = st.selectbox(
        "Simulation",
        options=options,
        index=options.index(default_sim),
        format_func=lambda x: (
            f"#{x} · {sims.loc[sims.simulation_id == x, 'sim_name'].iloc[0]}"
        ),
        key=key,
    )
    st.session_state["selected_simulation_id"] = sim_id
    return sim_id, sims


def render_api_error(exc: APIError) -> None:
    """Friendly error banner for failed backend calls."""
    if exc.status_code == 404:
        st.warning(str(exc))
    elif exc.status_code in (400, 422):
        st.error(f"Bad request: {exc}")
    else:
        st.error(f"Backend error: {exc}")


def inject_chart_styles() -> None:
    """Disable zoom/pan on all Vega-Lite charts (st.line_chart, st.bar_chart, etc.).

    Call once at the top of any page that renders charts.
    """
    st.markdown(
        """<style>
        /* Disable zoom/pan interaction on Vega-Lite chart canvases */
        [data-testid="stVegaLiteChart"] canvas {
            pointer-events: none !important;
        }
        </style>""",
        unsafe_allow_html=True,
    )


def render_sidebar_and_css() -> None:
    """Render the global sidebar and inject navigation CSS across all pages."""
    
    # Hide the default sidebar navigation and style the pill buttons
    st.markdown(
        """
        <style>
        [data-testid='stSidebarNav'] { display: none; }
        div[data-testid="stSidebarContent"] { padding-top: 2rem; }
        
        /* Style for top navigation page links to look like pills */
        [data-testid="stPageLink-NavLink"] {
            background-color: #f1f3f5;
            border-radius: 8px;
            padding: 8px 12px;
            text-align: center;
            text-decoration: none;
            color: #333;
            font-weight: 500;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: background-color 0.2s;
            border: 1px solid #e9ecef;
        }
        [data-testid="stPageLink-NavLink"]:hover {
            background-color: #e9ecef;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar Content
    with st.sidebar:
        st.markdown("### CampX")
        
        st.markdown("**Description**")
        st.caption("CampX is a live contextual bandit demonstration that uses LinUCB to actively learn and assign optimal promotional actions to different customer segments.")
        
        st.markdown("**Main Features**")
        st.caption("- Live simulated customer environment\n- Real-time policy learning\n- Counterfactual performance evaluation")
        
        st.markdown("**Main Goals of the Model**")
        st.caption("- Maximize overall campaign profit\n- Personalize promotions dynamically\n- Balance exploration vs. exploitation")
        
        st.markdown("**Our Advantages**")
        st.caption("- Adaptive to changing behaviors\n- Cost-aware action selection\n- Continuous interactive learning")


def render_top_navigation() -> None:
    """Render the top navigation buttons."""
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.page_link("app.py", label="Home", icon="🏠", use_container_width=True)
    c2.page_link("pages/1_create_simulation.py", label="Create", icon="🚀", use_container_width=True)
    c3.page_link("pages/2_interaction.py", label="Interaction", icon="⚡", use_container_width=True)
    c4.page_link("pages/3_analytics.py", label="Analytics", icon="📊", use_container_width=True)
    c5.page_link("pages/4_model.py", label="Model", icon="🧠", use_container_width=True)
    c6.page_link("pages/5_customers.py", label="Customers", icon="👥", use_container_width=True)
    
    st.write("") # Spacer


def render_global_navigation() -> None:
    """Convenience function to render both sidebar and top navigation."""
    render_sidebar_and_css()
    render_top_navigation()