"""
Campaign Optimization Engine — Streamlit entry point.
Owner: Armine Babajanyan (frontend branch)

M2: Navigation skeleton, landing page, KPI tiles with mock data.
M3: Flip USE_MOCKS = False in bandit_utils.py, wire real endpoints.

Pages under pages/ are auto-discovered by Streamlit.
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(
    page_title="Campaign Optimization Engine",
    layout="wide",
)

# ── Hero ──────────────────────────────────────────────────────
st.title("Campaign Optimization Engine")
st.markdown(
    "A **contextual bandit (LinUCB)** that learns which promotional action "
    "maximises profit for each fashion retail customer — updating after "
    "every interaction."
)
st.caption("DS 223 · Marketing Analytics · Group 1 · AUA Spring 2026")

st.divider()

# ── KPI tiles ─────────────────────────────────────────────────
st.subheader("System status")

sims = bu.list_simulations()
total_sims = len(sims)
running = int((sims["status"] == "running").sum()) if total_sims else 0
best = sims["cumulative_reward"].max() if total_sims else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Simulations run", total_sims)
c2.metric("Currently running", running)
c3.metric("Best cumulative reward", bu.format_currency(best))
c4.metric("Customer pool", "500")

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
st.dataframe(action_df, hide_index=True, use_container_width=True)

st.divider()

# ── Navigation cards ───────────────────────────────────────────
st.subheader("Where next?")
n1, n2, n3, n4 = st.columns(4)
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

st.divider()

with st.expander("📦 M2 status"):
    st.markdown(
        """
        **This is a skeleton build.** All pages use mock data.
        API integration lands in **M3** — see `docs/frontend.md` for the
        backend contract Victoria will implement.

        - ✅ Navigation skeleton
        - ✅ Layout + placeholders on all 4 pages
        - ✅ Backend contract documented
        - ⏳ Real API calls (M3)
        - ⏳ Live auto-refresh (M3)
        """
    )