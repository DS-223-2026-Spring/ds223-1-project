"""
Page 1 — Create Simulation
Owner: Armine Babajanyan (frontend branch)

M2: Form layout + past-simulations table with mock data.
M3: Wire submit → POST /simulate; table → GET /simulations with polling.

Backend endpoints consumed:
  POST /simulate       : create and trigger a new run
  GET  /simulations    : list past and running simulations
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(
    page_title="Create Simulation · CampX",
    layout="wide",
)

st.title("Create Simulation")
st.caption("Configure a new bandit run or inspect past ones.")

# ── Launch form ────────────────────────────────────────────────
st.subheader("Launch a new simulation")

with st.form("new_simulation", clear_on_submit=False):
    c1, c2 = st.columns(2)
    with c1:
        sim_name = st.text_input(
            "Name",
            placeholder="e.g. baseline_alpha_0.5",
            help="Human-readable label for this run.",
        )
        num_rounds = st.number_input(
            "Rounds", min_value=100, max_value=50000,
            value=5000, step=500,
            help="How many (customer, action) decisions to simulate.",
        )
        num_customers = st.number_input(
            "Customers", min_value=50, max_value=10000,
            value=500, step=50,
            help="Size of the customer pool LinUCB samples from.",
        )
    with c2:
        alpha = st.slider(
            "Alpha (exploration)", 0.0, 2.0, 0.5, 0.1,
            help="Higher α → more exploration. Lower α → more exploitation.",
        )
        baselines = st.multiselect(
            "Compare against baselines",
            ["Random", "Heuristic"],
            default=["Random", "Heuristic"],
            help="Run these policies on the same customer stream.",
        )
        notes = st.text_area("Notes", placeholder="Why this run?", height=100)

    submitted = st.form_submit_button(
        "▶ Launch run", type="primary", width='stretch'
    )

if submitted:
    if not sim_name.strip():
        st.error("Please enter a name.")
    else:
        resp = bu.create_simulation(
            sim_name=sim_name,
            num_rounds=int(num_rounds),
            num_customers=int(num_customers),
            alpha=float(alpha),
            notes=notes,
        )
        st.success(
            f"Simulation `{resp['sim_name']}` queued "
            f"(id: {resp['simulation_id']}). Open Interaction to watch."
        )
        st.info("⚠️ M2 placeholder — Prefect wiring lands in M3.")

st.divider()

# ── Past simulations ───────────────────────────────────────────
st.subheader("Past simulations")

sims = bu.list_simulations()

if sims.empty:
    st.info("No simulations yet. Launch one above.")
else:
    display = sims.copy()
    display["started_at"] = display["started_at"].dt.strftime("%Y-%m-%d %H:%M")
    display["completed_at"] = display["completed_at"].apply(
        lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notna(x) else "—"
    )
    display["cumulative_reward"] = display["cumulative_reward"].apply(
        lambda x: f"£{x:,.2f}" if pd.notna(x) else "—"
    )

    st.dataframe(
        display[[
            "simulation_id", "sim_name", "status", "num_rounds",
            "num_customers", "alpha", "started_at",
            "completed_at", "cumulative_reward",
        ]],
        hide_index=True,
        width='stretch',
        column_config={
            "simulation_id": "ID",
            "sim_name": "Name",
            "status": "Status",
            "num_rounds": "Rounds",
            "num_customers": "Customers",
            "alpha": "α",
            "started_at": "Started",
            "completed_at": "Completed",
            "cumulative_reward": "Cum. reward",
        },
    )

    sim_id = st.selectbox(
        "Select a simulation to open",
        options=sims["simulation_id"].tolist(),
        format_func=lambda x: (
            f"#{x} · {sims.loc[sims.simulation_id == x, 'sim_name'].iloc[0]}"
        ),
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Watch live (Interaction) →",
                     width='stretch'):
            st.session_state["selected_simulation_id"] = sim_id
            st.switch_page("pages/2_interaction.py")
    with col_b:
        if st.button("See results (Analytics) →",
                     width='stretch'):
            st.session_state["selected_simulation_id"] = sim_id
            st.switch_page("pages/3_analytics.py")