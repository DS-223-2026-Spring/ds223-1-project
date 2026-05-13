"""
Campaign Optimization Engine — Streamlit entry point.
Owner: Armine Babajanyan (frontend branch)
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

import base64
from pathlib import Path

APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "assets" / "campx_logo.png"

try:
    with open(LOGO_PATH, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode("utf-8")
except FileNotFoundError:
    logo_b64 = ""

st.set_page_config(
    page_title="CampX",
    layout="wide",
)

bu.render_sidebar_and_css()

# ── Business Context Banner ───────────────────────────────────
# ── Hero ──────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    .hero-container {{
        margin: 0.5rem 0 1.5rem 0;
        padding: 2.5rem 3rem;
        border: 1px solid color-mix(in srgb, var(--text-color) 15%, transparent);
        border-radius: 20px;
        background: color-mix(in srgb, var(--secondary-background-color) 70%, transparent);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: 0 10px 32px color-mix(in srgb, var(--text-color) 15%, transparent);
        display: flex;
        align-items: center;
        gap: 2.5rem;
    }}
    .hero-content {{
        flex: 1;
    }}
    .hero-kicker {{
        font-size: 0.8rem;
        font-weight: 800;
        letter-spacing: 0.15em;
        color: var(--primary-color);
        margin-bottom: 0.8rem;
        text-transform: uppercase;
    }}
    .hero-title {{
        font-size: 2.8rem;
        font-weight: 850;
        color: var(--text-color);
        line-height: 1.15;
        margin-bottom: 0.8rem;
        letter-spacing: -0.02em;
    }}
    .hero-subtitle {{
        font-size: 1.15rem;
        color: var(--text-color);
        opacity: 0.8;
        line-height: 1.6;
        max-width: 650px;
    }}
    .hero-logo-wrapper {{
        flex-shrink: 0;
        width: 140px;
        height: 140px;
        border-radius: 24px;
        overflow: hidden;
        box-shadow: 0 12px 24px color-mix(in srgb, var(--primary-color) 30%, transparent);
        border: 2px solid color-mix(in srgb, var(--text-color) 10%, transparent);
    }}
    .hero-logo-wrapper img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}
    </style>

    <div class="hero-container">
        <div class="hero-content">
            <div class="hero-kicker">Campaign Optimization Engine</div>
            <div class="hero-title">Camp<span style="color: var(--primary-color);">X</span></div>
            <div class="hero-subtitle">
                CampX helps marketing teams choose the right promotion for the right customer. It uses customer behavior and campaign outcomes to learn which offers create incremental value, reducing wasted discounts and improving campaign profitability over time.
            </div>
        </div>
        <div class="hero-logo-wrapper">
            <img src="data:image/png;base64,{logo_b64}" alt="CampX Contextual Bandit Logo" />
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("") # Spacer
bu.render_top_navigation()
st.write("") # Spacer

# ── KPI tiles ─────────────────────────────────────────────────
st.subheader("System status")

try:
    sims = bu.list_simulations()
except bu.APIError as exc:
    bu.render_api_error(exc)
    sims = pd.DataFrame()

try:
    customers = bu.list_customers()
    customer_count = len(customers)
except bu.APIError:
    customer_count = 0

total_sims = len(sims)
running = int((sims["status"] == "running").sum()) if total_sims and "status" in sims else 0
best = sims["cumulative_reward"].max() if total_sims and "cumulative_reward" in sims else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Simulations run", total_sims)
c2.metric("Currently running", running)
c3.metric("Best cumulative reward", bu.format_currency(best))
c4.metric("Customer pool", customer_count)

st.write("") # Spacer
st.write("") # Spacer
# ── Action catalog ────────────────────────────────────────────
st.subheader("Action catalog")
st.write("The five promotional arms. LinUCB picks one per customer per decision.")

intended_segments = [
    "Champions — buy regardless",
    "Price-sensitive, lapsed",
    "Moderate-basket planners",
    "Loyal, engaged browsers",
    "Impulse buyers with basket diversity",
]
action_df = pd.DataFrame([
    {
        "Action": bu.ACTION_LABELS[k],
        "Cost to brand": bu.format_currency(v),
        "Intended segment": segment,
    }
    for (k, v), segment in zip(bu.ACTION_COSTS.items(), intended_segments)
])
st.dataframe(action_df, hide_index=True, width="stretch")

