"""
Page 1 — Create Simulation
Owner: Armine Babajanyan (frontend branch)

Wired to:
  POST /simulations    : create a new run
  GET  /simulations    : list past and running simulations

Built-in Streamlit components only.
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(
    page_title="Create Simulation · CampX",
    layout="wide",
)

bu.render_global_navigation()

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
            help="Human-readable label for this run. Must be unique.",
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
        notes = st.text_area("Notes", placeholder="Why this run?", height=100)

    submitted = st.form_submit_button(
        "▶ Launch run", type="primary", width="stretch",
    )

if submitted:
    if not sim_name.strip():
        st.error("Please enter a name.")
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
            st.success(
                f"Simulation `{resp['sim_name']}` created "
                f"(id: {resp['simulation_id']}). "
                "Open Interaction to watch it run."
            )
            st.info("ℹ️ Simulation queued. DS pipeline will process it.")
            # Fresh-fetch the simulations list on next render
            bu.list_simulations.clear()

st.divider()

# ── Past simulations ───────────────────────────────────────────
st.subheader("Past simulations")

try:
    sims = bu.list_simulations()
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

if sims.empty:
    st.info("No simulations yet. Launch one above.")
    st.stop()

# Filters
fcol1, fcol2, fcol3 = st.columns([1, 1, 2])
with fcol1:
    status_options = ["All"] + sorted(sims["status"].dropna().unique().tolist()) \
        if "status" in sims else ["All"]
    status_filter = st.selectbox("Status", options=status_options, index=0)
with fcol2:
    name_filter = st.text_input("Name contains", value="", placeholder="filter…")
with fcol3:
    st.caption(" ")  # vertical alignment

display = sims.copy()
if status_filter != "All" and "status" in display:
    display = display[display["status"] == status_filter]
if name_filter:
    display = display[display["sim_name"].str.contains(name_filter, case=False, na=False)]

# Friendly formatting for the table
fmt = display.copy()
if "started_at" in fmt:
    fmt["started_at"] = fmt["started_at"].apply(
        lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notna(x) else "—"
    )
if "completed_at" in fmt:
    fmt["completed_at"] = fmt["completed_at"].apply(
        lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notna(x) else "—"
    )
if "cumulative_reward" in fmt:
    fmt["cumulative_reward"] = fmt["cumulative_reward"].apply(
        lambda x: f"£{x:,.2f}" if pd.notna(x) else "—"
    )

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

if display.empty:
    st.caption("No simulations match the current filters.")
    st.stop()

# ── Quick-jump to other pages with the selected sim ─────────────
sim_id = st.selectbox(
    "Select a simulation to open",
    options=display["simulation_id"].tolist(),
    format_func=lambda x: (
        f"#{x} · {display.loc[display.simulation_id == x, 'sim_name'].iloc[0]}"
    ),
)
col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("Watch live (Interaction) →", width="stretch"):
        st.session_state["selected_simulation_id"] = sim_id
        st.switch_page("pages/2_interaction.py")
with col_b:
    if st.button("See results (Analytics) →", width="stretch"):
        st.session_state["selected_simulation_id"] = sim_id
        st.switch_page("pages/3_analytics.py")
with col_c:
    if st.button("Inspect model →", width="stretch"):
        st.session_state["selected_simulation_id"] = sim_id
        st.switch_page("pages/4_model.py")