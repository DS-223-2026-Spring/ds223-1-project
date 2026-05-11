"""
Campaign Optimization Engine — Streamlit entry point.
Owner: Armine Babajanyan (frontend branch)

M3: Wired to live FastAPI backend. Uses only built-in Streamlit components.
Pages under pages/ are auto-discovered by Streamlit.
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(
    page_title="CampX",
    layout="wide",
)

# Capitalize every word in sidebar navigation labels
st.markdown(
    "<style>[data-testid='stSidebarNav'] span { text-transform: capitalize; }</style>",
    unsafe_allow_html=True,
)

# ── Hero ──────────────────────────────────────────────────────
st.title("CampX")
st.markdown(
    "A **contextual bandit (LinUCB)** that learns which promotional action "
    "maximises profit for each fashion retail custome.r"
)


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

st.divider()

# ── Navigation cards ───────────────────────────────────────────
st.subheader("Where next?")
n1, n2, n3, n4, n5 = st.columns(5)
with n1:
    st.markdown("### Create Simulation")
    st.caption("Configure and launch a new run.")
    st.page_link("pages/1_create_simulation.py", label="Open →")
with n2:
    st.markdown("### Interaction")
    st.caption("Watch the live bandit loop as it runs.")
    st.page_link("pages/2_interaction.py", label="Open →")
with n3:
    st.markdown("### Analytics")
    st.caption("Compare policies, inspect results, review interactions.")
    st.page_link("pages/3_analytics.py", label="Open →")
with n4:
    st.markdown("### Model")
    st.caption("θ vectors, pull counts, UCB decomposition.")
    st.page_link("pages/4_model.py", label="Open →")
with n5:
    st.markdown("### Customers")
    st.caption("Browse & filter customer profiles.")
    st.page_link("pages/5_customers.py", label="Open →")

st.divider()
