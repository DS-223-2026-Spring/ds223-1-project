"""
bandit_utils.py — shared API client, theme constants, product copy, and formatters.

Owner: Armine Babajanyan (frontend branch)
"""
from __future__ import annotations

import os
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
# Product/theme constants
# ═════════════════════════════════════════════════════════════
NAVY = "#0f172a"
SLATE = "#334155"
MUTED = "#64748b"
TEAL = "#0f766e"
TEAL_BRIGHT = "#14b8a6"
SOFT_BG = "#f8fafc"
SOFT_TEAL = "#eef7f6"
BORDER = "rgba(15, 118, 110, 0.16)"

ACTION_COLORS = {
    "no_action": "#64748b",              # slate
    "discount_10": "#0f766e",            # teal
    "free_shipping": "#2563eb",          # blue
    "product_recommendation": "#14b8a6", # bright teal
    "bundle_offer": "#7c3aed",           # violet
}

ACTION_LABELS = {
    "no_action": "No action",
    "discount_10": "10% off",
    "free_shipping": "Free shipping",
    "product_recommendation": "Product recommendation",
    "bundle_offer": "Bundle",
}

ACTION_COSTS = {
    "no_action": 0.00,
    "discount_10": 6.50,
    "free_shipping": 4.99,
    "product_recommendation": 0.30,
    "bundle_offer": 9.00,
}

RFM_FEATURES = [
    "recency",
    "frequency",
    "monetary",
    "basket_diversity",
    "avg_order_size",
    "purchase_regularity",
]

SEGMENT_DEFINITIONS = {
    "Champion": "High-value customers with strong recent purchase behavior.",
    "Loyal": "Repeat customers with consistent engagement.",
    "At-Risk": "Customers whose behavior suggests weakening engagement.",
    "Lost": "Customers with low recent activity or weak purchase signals.",
}


def format_currency(value, round_int=False) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if round_int:
        return f"£{int(round(float(value))):,}"
    return f"£{float(value):,.2f}"


def format_pct(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"{float(value) * 100:.1f}%"


def friendly_action(action: str) -> str:
    return ACTION_LABELS.get(action, action)


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
        try:
            payload = resp.json()
            detail = payload.get("detail") or payload.get("message") or payload
        except ValueError:
            detail = resp.text or resp.reason
        raise APIError(
            f"{method} {path} → {resp.status_code}: {detail}",
            status_code=resp.status_code,
        )

    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def _to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)


# ═════════════════════════════════════════════════════════════
# Health / status
# ═════════════════════════════════════════════════════════════
def backend_health() -> dict:
    return _request("GET", "/health")


# ═════════════════════════════════════════════════════════════
# Campaign runs / simulations
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=10, show_spinner=False)
def list_simulations() -> pd.DataFrame:
    payload = _request("GET", "/simulations")
    if not payload:
        return pd.DataFrame(columns=[
            "simulation_id", "sim_name", "num_rounds", "num_customers",
            "alpha", "started_at", "completed_at", "status", "cumulative_reward",
        ])
    df = pd.DataFrame(payload)
    if "started_at" in df.columns:
        df["started_at"] = _to_datetime(df["started_at"])
    if "completed_at" in df.columns:
        df["completed_at"] = _to_datetime(df["completed_at"])
    return df


def create_simulation(sim_name: str, num_rounds: float, num_customers: float,
                      alpha: float, notes: str = "") -> dict:
    body = {
        "sim_name": sim_name,
        "num_rounds": int(num_rounds),
        "num_customers": int(num_customers),
        "alpha": float(alpha),
        "notes": notes or None,
    }
    return _request("POST", "/simulations", json=body)


# ═════════════════════════════════════════════════════════════
# Metrics
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=15, show_spinner=False)
def get_metrics(simulation_id: int) -> dict:
    raw = _request("GET", "/metrics", params={"simulation_id": simulation_id}) or {}

    total_interactions = int(raw.get("total_interactions", 0) or 0)
    total_reward = float(raw.get("total_reward", 0.0) or 0.0)
    avg_reward = (total_reward / total_interactions) if total_interactions else 0.0

    cum_series = pd.DataFrame(raw.get("cumulative_reward_series") or [])
    action_dist = pd.DataFrame(raw.get("action_distribution") or [])
    conv_by_action = pd.DataFrame(raw.get("conversion_by_action") or [])
    segment_perf = pd.DataFrame(raw.get("segment_performance") or [])
    recent = pd.DataFrame(raw.get("recent_interactions") or [])

    if not recent.empty:
        if "decision_at" in recent.columns:
            recent["decision_at"] = _to_datetime(recent["decision_at"])
        if "decision_at" not in recent.columns and "decision_at" in raw:
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
        "cumulative_reward_series": cum_series,
        "action_distribution": action_dist,
        "conversion_by_action": conv_by_action,
        "segment_performance": segment_perf,
        "recent_interactions": recent,
    }


@st.cache_data(ttl=60, show_spinner=False)
def get_baselines() -> list[float]:
    raw = _request("GET", "/baselines")
    if raw and "random_baseline_rewards" in raw:
        return raw["random_baseline_rewards"]
    return []


# ═════════════════════════════════════════════════════════════
# Customers
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=60, show_spinner=False)
def list_customers() -> pd.DataFrame:
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
    for col in RFM_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=30, show_spinner=False)
def get_customer(customer_id: int, debug: bool = False) -> dict:
    params = {"debug": "true"} if debug else None
    return _request("GET", f"/customers/{int(customer_id)}", params=params)


# ═════════════════════════════════════════════════════════════
# Model state
# ═════════════════════════════════════════════════════════════
@st.cache_data(ttl=15, show_spinner=False)
def get_model_state(simulation_id: int) -> dict:
    raw = _request("GET", "/model/state", params={"simulation_id": simulation_id})
    n_pulls = dict(raw.get("n_pulls") or {})
    for action_name in ACTION_LABELS:
        n_pulls.setdefault(action_name, 0)

    theta_raw = raw.get("theta") or {}
    if theta_raw:
        theta_df = pd.DataFrame.from_dict(theta_raw, orient="index").reindex(index=RFM_FEATURES)
    else:
        theta_df = pd.DataFrame(
            np.zeros((len(RFM_FEATURES), len(ACTION_LABELS))),
            index=RFM_FEATURES,
            columns=list(ACTION_LABELS.keys()),
        )
    theta_df = theta_df.reindex(columns=list(ACTION_LABELS.keys()), fill_value=0.0)

    return {
        "alpha": float(raw.get("alpha", 0.0) or 0.0),
        "round_number": int(raw.get("round_number", 0) or 0),
        "updated_at": raw.get("updated_at"),
        "n_pulls": n_pulls,
        "theta": theta_df,
    }


def predict_for_customer(simulation_id: int, customer_id: int) -> pd.DataFrame:
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
    return df.sort_values("ucb_score", ascending=False).reset_index(drop=True)


# ═════════════════════════════════════════════════════════════
# Shared UI helpers
# ═════════════════════════════════════════════════════════════
def select_simulation_widget(key: str = "sim_select", label: str = "Campaign run"):
    try:
        sims = list_simulations()
    except APIError as exc:
        st.error(f"Could not load campaign runs: {exc}")
        return None, pd.DataFrame()

    if sims.empty:
        return None, sims

    options = sims["simulation_id"].tolist()
    default_sim = st.session_state.get("selected_simulation_id", options[0])
    if default_sim not in options:
        default_sim = options[0]

    sim_id = st.selectbox(
        label,
        options=options,
        index=options.index(default_sim),
        format_func=lambda x: f"#{x} · {sims.loc[sims.simulation_id == x, 'sim_name'].iloc[0]}",
        key=key,
    )
    st.session_state["selected_simulation_id"] = sim_id
    return sim_id, sims


def render_api_error(exc: APIError) -> None:
    if exc.status_code == 404:
        st.warning(str(exc))
    elif exc.status_code in (400, 422):
        st.error(f"Bad request: {exc}")
    else:
        st.error(f"Backend error: {exc}")


def render_mvp_note() -> None:
    st.caption(
        "MVP note: this app uses synthetic retail-style customer data to demonstrate the campaign optimization workflow."
    )


def render_reward_note() -> None:
    st.caption("Reward = realized revenue from conversion − promotional action cost.")


def render_sidebar_and_css() -> None:
    """Render global sidebar and inject product-grade CSS."""
    st.markdown(
        f"""
        <style>
        [data-testid='stSidebarNav'] {{ display: none; }}
        div[data-testid="stSidebarContent"] {{ padding-top: 1.5rem; }}

        .block-container {{
            padding-top: 2.35rem !important;
            padding-bottom: 4rem !important;
            max-width: 1420px;
        }}

        h1, h2, h3 {{
            font-weight: 800 !important;
            color: {NAVY};
            letter-spacing: -0.025em;
        }}

        p, label, span, div {{
            font-family: inherit;
        }}

        [data-testid="stPageLink-NavLink"] {{
            background-color: #ffffff;
            border-radius: 10px;
            padding: 10px 14px;
            margin: 0 5px;
            text-align: center;
            text-decoration: none;
            color: #475569;
            font-weight: 650;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: all 0.18s ease-in-out;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 2px rgba(15,23,42,0.05);
            min-height: 42px;
        }}
        [data-testid="stPageLink-NavLink"]:hover {{
            color: {NAVY};
            background-color: #f8fafc;
            border-color: #cbd5e1;
            transform: translateY(-1px);
        }}
        [data-testid="stPageLink-NavLink"][data-active="true"],
        [data-testid="stPageLink-NavLink"]:active {{
            background-color: #ffffff;
            color: {TEAL};
            border-color: {TEAL};
            box-shadow: 0 2px 6px rgba(15, 118, 110, 0.16);
        }}

        [data-testid="stButton"] button[kind="primary"],
        [data-testid="stFormSubmitButton"] button[kind="primary"] {{
            background: {TEAL} !important;
            border: 1px solid {TEAL} !important;
            color: white !important;
            font-weight: 700 !important;
            border-radius: 10px !important;
        }}
        [data-testid="stButton"] button[kind="primary"]:hover,
        [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {{
            background: #0b5f59 !important;
            border-color: #0b5f59 !important;
        }}

        [data-testid="stVegaLiteChart"],
        [data-testid="stArrowVegaLiteChart"] {{
            pointer-events: none !important;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid rgba(15, 23, 42, 0.10);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(15,23,42,0.025);
        }}

        [data-testid="stMetric"] {{
            background-color: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            box-shadow: 0 5px 14px rgba(15, 23, 42, 0.035);
            border-radius: 14px;
            padding: 1rem 1.25rem;
            transition: all 0.18s ease-in-out;
        }}
        [data-testid="stMetric"]:hover {{
            transform: translateY(-1px);
            box-shadow: 0 10px 18px rgba(15, 118, 110, 0.08);
            border-color: rgba(15, 118, 110, 0.22);
        }}
        [data-testid="stMetricValue"] {{
            font-weight: 800 !important;
            color: {TEAL} !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-weight: 650 !important;
            color: {MUTED} !important;
            font-size: 0.82rem !important;
            text-transform: uppercase;
            letter-spacing: 0.055em;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### CampX")
        st.caption("Promotion decision support")
        st.write("")
        st.markdown("**Overview**")
        st.write(
            "CampX helps marketing teams compare promotional actions, monitor campaign value, "
            "and allocate incentives based on customer behavior."
        )
        st.write("")
        st.markdown("**MVP scope**")
        st.write(
            "This course MVP uses synthetic retail-style customer data to demonstrate an end-to-end "
            "campaign optimization workflow."
        )
        with st.expander("Technical note"):
            st.write(
                "The decision policy uses a LinUCB contextual bandit. It balances exploration "
                "(collecting feedback for uncertain actions) and exploitation (using actions with stronger learned value)."
            )
            st.write("Reward is modeled as realized revenue minus action cost.")


def render_top_navigation() -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.page_link("app.py", label="Home", use_container_width=True)
    c2.page_link("pages/1_create_simulation.py", label="Campaign Setup", use_container_width=True)
    c3.page_link("pages/2_interaction.py", label="Live Decisions", use_container_width=True)
    c4.page_link("pages/3_analytics.py", label="Performance", use_container_width=True)
    c5.page_link("pages/4_model.py", label="Decision Logic", use_container_width=True)
    c6.page_link("pages/5_customers.py", label="Customers", use_container_width=True)
    st.write("")


def render_global_navigation() -> None:
    render_sidebar_and_css()
    render_top_navigation()
