"""
Page 2 — Interaction
Owner: Armine Babajanyan (frontend branch)

This page is the live bandit loop — where LinUCB is actively assigning
actions to customers and accumulating reward.

M2: Layout + chart placeholders using mock data.
M3: Connect to GET /metrics, 30s auto-refresh while status == "running".

Backend endpoints consumed:
  GET /simulations                  : selector
  GET /metrics?simulation_id=...    : all live aggregates
"""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import bandit_utils as bu

st.set_page_config(
    page_title="Interaction · CampX",
    layout="wide",
)

st.title("Live Interaction")
st.caption("LinUCB is picking actions for customers. Watch it learn.")

# ── Simulation selector ────────────────────────────────────────
sim_id, sims = bu.select_simulation_widget(key="interaction_sim")
if sim_id is None:
    st.info("No simulations yet. Launch one on **Create Simulation**.")
    st.stop()

# ── Controls ───────────────────────────────────────────────────
c1, c2 = st.columns([1, 1])
with c1:
    auto_refresh = st.toggle(
        "Auto-refresh", value=False,
        help="Re-fetch metrics every 30s (active in M3).",
    )
with c2:
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()

metrics = bu.get_metrics(sim_id)

# ── KPI tiles ──────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Rounds completed", f"{metrics['rounds_completed']:,}")
k2.metric("Cumulative reward",
          bu.format_currency(metrics["cumulative_reward"]))
k3.metric("Avg reward / round", f"£{metrics['avg_reward_per_round']:.2f}")
k4.metric(
    "Pending observations", metrics["pending_observations"],
    help="Interactions still inside the conversion window.",
)

st.divider()

# ── Cumulative reward chart ────────────────────────────────────
st.subheader("Cumulative reward")
st.caption("LinUCB versus baselines over rounds. Higher = better.")

cum = metrics["cumulative_reward_series"]
fig = go.Figure()
fig.add_scatter(x=cum["round"], y=cum["linucb"],
                mode="lines", name="LinUCB",
                line=dict(width=2.5, color="#1E293B"))
fig.add_scatter(x=cum["round"], y=cum["heuristic"],
                mode="lines", name="Heuristic",
                line=dict(width=1.5, dash="dash", color="#94A3B8"))
fig.add_scatter(x=cum["round"], y=cum["random"],
                mode="lines", name="Random",
                line=dict(width=1.5, dash="dot", color="#CBD5E1"))
fig.update_layout(
    xaxis_title="Round",
    yaxis_title="Cumulative reward (£)",
    height=400,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(t=20, b=20),
    plot_bgcolor="white",
    yaxis=dict(showgrid=False),
    xaxis=dict(showgrid=False),
)
st.plotly_chart(fig, width='stretch')

st.divider()

# ── Recent interactions table ──────────────────────────────────
st.subheader("Recent interactions")
st.caption("The last 20 decisions LinUCB has made.")

ri = metrics["recent_interactions"].copy()
ri["action"] = ri["action"].map(bu.ACTION_LABELS)
ri["decision_at"] = ri["decision_at"].dt.strftime("%H:%M:%S")
ri["revenue"] = ri["revenue"].map(lambda x: f"£{x:.2f}")
ri["reward"] = ri["reward"].map(lambda x: f"£{x:+.2f}")

st.dataframe(
    ri[["interaction_id", "decision_at", "customer_id",
        "action", "converted", "revenue", "reward"]],
    hide_index=True,
    width='stretch',
    column_config={
        "interaction_id": "ID",
        "decision_at": "Time",
        "customer_id": "Customer",
        "action": "Action",
        "converted": "Converted",
        "revenue": "Revenue",
        "reward": "Reward",
    },
)

st.caption("⚠️ M2: values from mock generator. Wired to /metrics in M3.")