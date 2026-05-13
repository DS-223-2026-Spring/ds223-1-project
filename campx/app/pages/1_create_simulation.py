"""
Page 1 — Campaign Setup
Owner: Armine Babajanyan (frontend branch)
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(page_title="Campaign Setup · CampX", layout="wide")
bu.render_global_navigation()

st.title("Campaign Setup")
st.caption("Configure a new campaign run or inspect previous runs.")
bu.render_mvp_note()

# ── Launch form ────────────────────────────────────────────────
st.subheader("Launch a new campaign run")
st.caption("For the final demo, use a short run if launching live. Keep one known-good completed run available as backup.")

with st.form("new_simulation", clear_on_submit=False):
    c1, c2 = st.columns(2)
    with c1:
        sim_name = st.text_input(
            "Run name",
            placeholder="e.g. demo_alpha_0_8_seed42",
            help="Human-readable label for this campaign run. Must be unique.",
        )
        num_rounds = st.number_input(
            "Decision rounds",
            min_value=100,
            max_value=50000,
            value=5000,
            step=500,
            help="Number of customer-action decisions to simulate.",
        )
        num_customers = st.number_input(
            "Customer pool size",
            min_value=50,
            max_value=10000,
            value=500,
            step=50,
            help="Number of customers available to the decision policy.",
        )
    with c2:
        alpha = st.slider(
            "Alpha: exploration strength",
            0.0,
            2.0,
            0.8,
            0.1,
            help="Higher α collects more evidence for uncertain actions. Lower α exploits learned high-value actions sooner.",
        )
        notes = st.text_area("Notes", placeholder="Purpose of this run", height=100)

    submitted = st.form_submit_button("Launch campaign run", type="primary", width="stretch")

if submitted:
    if not sim_name.strip():
        st.error("Please enter a run name.")
    else:
        try:
            resp = bu.create_simulation(
                sim_name=sim_name.strip(),
                num_rounds=int(num_rounds),
                num_customers=int(num_customers),
                alpha=float(alpha),
                notes=notes,
            )
        except bu.APIError as exc:
            bu.render_api_error(exc)
        else:
            st.session_state["selected_simulation_id"] = resp["simulation_id"]
            st.success(
                f"Campaign run `{resp['sim_name']}` created "
                f"(id: {resp['simulation_id']}). Open Live Decisions to monitor it."
            )
            bu.list_simulations.clear()
            bu.get_metrics.clear()
            bu.get_model_state.clear()

st.write("")

# ── Past campaign runs ─────────────────────────────────────────
st.subheader("Past campaign runs")

try:
    sims = bu.list_simulations()
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

if sims.empty:
    st.info("No campaign runs yet. Launch one above.")
    st.stop()

fcol1, fcol2, fcol3 = st.columns([1, 1, 2])
with fcol1:
    status_options = ["All"] + sorted(sims["status"].dropna().unique().tolist()) if "status" in sims else ["All"]
    status_filter = st.selectbox("Status", options=status_options, index=0)
with fcol2:
    name_filter = st.text_input("Run name contains", value="", placeholder="filter…")
with fcol3:
    st.caption(" ")

display = sims.copy()
if status_filter != "All" and "status" in display:
    display = display[display["status"] == status_filter]
if name_filter:
    display = display[display["sim_name"].str.contains(name_filter, case=False, na=False)]

fmt = display.copy()
if "started_at" in fmt:
    fmt["started_at"] = fmt["started_at"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notna(x) else "—")
if "completed_at" in fmt:
    fmt["completed_at"] = fmt["completed_at"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notna(x) else "—")
if "cumulative_reward" in fmt:
    fmt["cumulative_reward"] = fmt["cumulative_reward"].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "—")

cols_to_show = [c for c in [
    "simulation_id", "sim_name", "status", "num_rounds",
    "num_customers", "alpha", "started_at",
    "completed_at", "cumulative_reward",
] if c in fmt.columns]

st.dataframe(
    fmt[cols_to_show],
    hide_index=True,
    width="stretch",
    column_config={
        "simulation_id": "ID",
        "sim_name": "Run name",
        "status": "Status",
        "num_rounds": "Rounds",
        "num_customers": "Customers",
        "alpha": "α",
        "started_at": "Started",
        "completed_at": "Completed",
        "cumulative_reward": "Cum. reward",
    },
)

if display.empty:
    st.caption("No campaign runs match the current filters.")
    st.stop()

sim_id = st.selectbox(
    "Select a campaign run to open",
    options=display["simulation_id"].tolist(),
    format_func=lambda x: f"#{x} · {display.loc[display.simulation_id == x, 'sim_name'].iloc[0]}",
)

col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("Monitor live decisions →", width="stretch"):
        st.session_state["selected_simulation_id"] = sim_id
        st.switch_page("pages/2_interaction.py")
with col_b:
    if st.button("View performance →", width="stretch"):
        st.session_state["selected_simulation_id"] = sim_id
        st.switch_page("pages/3_analytics.py")
with col_c:
    if st.button("Review decision logic →", width="stretch"):
        st.session_state["selected_simulation_id"] = sim_id
        st.switch_page("pages/4_model.py")
