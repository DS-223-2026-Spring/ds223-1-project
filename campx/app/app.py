"""
Campaign Optimization Engine — Streamlit entry point.
Owner: Armine Babajanyan (frontend branch)
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(
    page_title="CampX",
    layout="wide",
)

bu.render_sidebar_and_css()

# ── Hero ──────────────────────────────────────────────────────
# Logo in a white rounded container — works in both dark and light mode
st.markdown(
    """
    <div style="
        max-width: 480px;
        margin: 1.5rem auto;
        background: #ffffff;
        border-radius: 16px;
        padding: 1.2rem 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    ">
        <svg width="100%" viewBox="0 0 680 280" role="img" xmlns="http://www.w3.org/2000/svg">
            <circle cx="220" cy="140" r="62" fill="none" stroke="#1e40af" stroke-width="10"/>
            <circle cx="220" cy="140" r="40" fill="none" stroke="#3b82f6" stroke-width="8"/>
            <circle cx="220" cy="140" r="22" fill="#dc2626"/>
            <line x1="208" y1="128" x2="232" y2="152" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
            <line x1="232" y1="128" x2="208" y2="152" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
            <text x="310" y="162" fill="#141413"
                  style="font-size:60px; font-weight:500; letter-spacing:-1px;
                         font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif;">
                Camp<tspan fill="#dc2626">X</tspan>
            </text>
        </svg>
    </div>
    """,
    unsafe_allow_html=True,
)
st.title("CampX")
st.write("") # Spacer
bu.render_top_navigation()

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

st.divider()

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

