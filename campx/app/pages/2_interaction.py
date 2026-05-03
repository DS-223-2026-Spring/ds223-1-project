"""
Page 2 — Interaction
Owner: Armine Babajanyan (frontend branch)

Live bandit loop — LinUCB picking actions for customers.

Wired to:
  GET /simulations
  GET /metrics?simulation_id=...

Built-in Streamlit components only (st.line_chart, st.bar_chart,
st.dataframe, st.metric, st.toggle).

NOTE on /metrics: backend currently returns lightweight counters
(total_interactions, total_reward, total_revenue, total_cost,
conversions). The chart sections gracefully degrade when richer
arrays (cumulative_reward_series, recent_interactions, …) are missing.
"""
import time

import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(page_title="Interaction · CampX", layout="wide")

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
        "Auto-refresh (30s)", value=False,
        help="Re-fetch metrics every 30 seconds.",
    )
with c2:
    if st.button("🔄 Refresh now"):
        bu.get_metrics.clear()
        st.rerun()

# ── Fetch metrics ──────────────────────────────────────────────
try:
    metrics = bu.get_metrics(sim_id)
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

# ── KPI tiles ──────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Rounds completed", f"{metrics['rounds_completed']:,}")
k2.metric("Cumulative reward",
          bu.format_currency(metrics["cumulative_reward"]))
k3.metric("Avg reward / round",
          f"£{metrics['avg_reward_per_round']:.2f}")
pending = metrics.get("pending_observations")
k4.metric(
    "Pending observations",
    "—" if pending is None else f"{pending:,}",
    help="Interactions still inside the conversion window.",
)

# Secondary tiles using fields the backend reliably returns today
k5, k6, k7, k8 = st.columns(4)
k5.metric("Conversions", f"{metrics['conversions']:,}")
k6.metric("Total revenue", bu.format_currency(metrics["total_revenue"]))
k7.metric("Total cost", bu.format_currency(metrics["total_cost"]))
conv_rate = (metrics["conversions"] / metrics["rounds_completed"]
             if metrics["rounds_completed"] else 0.0)
k8.metric("Overall conversion rate", bu.format_pct(conv_rate))

st.divider()

# ── Cumulative reward chart ────────────────────────────────────
st.subheader("Cumulative reward")
cum = metrics.get("cumulative_reward_series")
if cum is None or cum.empty:
    st.info(
        "Cumulative reward series not yet available from `/metrics`. "
        "This chart will populate once the backend ships the "
        "`cumulative_reward_series` array."
    )
else:
    # Expect columns: round, linucb, [random, heuristic, …]
    chart_df = cum.copy()
    if "round" in chart_df.columns:
        chart_df = chart_df.set_index("round")
    st.line_chart(
        chart_df,
        height=380,
        y_label="Cumulative reward (£)",
        x_label="Round",
    )

st.divider()

# ── Action distribution over time ──────────────────────────────
st.subheader("Action distribution over time")
dist = metrics.get("action_distribution")
if dist is None or dist.empty:
    st.info(
        "Action distribution not yet available from `/metrics`. "
        "Will appear once the backend ships the "
        "`action_distribution` array."
    )
else:
    # Expect rows: {round, action}. Bin into buckets and stack-area chart.
    df = dist.copy()
    if "round" in df.columns:
        df["bucket"] = (df["round"] // 100) * 100
    else:
        df["bucket"] = df.index // 100 * 100
    counts = (
        df.groupby(["bucket", "action"]).size().unstack(fill_value=0).sort_index()
    )
    # Map technical names to friendly labels for display
    counts.columns = [bu.ACTION_LABELS.get(c, c) for c in counts.columns]
    st.area_chart(
        counts,
        height=320,
        stack=True,
        x_label="Round (binned by 100)",
        y_label="Times chosen",
    )

st.divider()

# ── Recent interactions table ──────────────────────────────────
st.subheader("Recent interactions")
ri = metrics.get("recent_interactions")
if ri is None or ri.empty:
    st.info(
        "Recent interactions not yet available from `/metrics`. "
        "Will appear once the backend ships the "
        "`recent_interactions` array."
    )
else:
    table = ri.copy()
    if "action" in table:
        table["action"] = table["action"].map(
            lambda a: bu.ACTION_LABELS.get(a, a)
        )
    if "decision_at" in table:
        table["decision_at"] = table["decision_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    if "revenue" in table:
        table["revenue"] = table["revenue"].apply(
            lambda x: f"£{x:.2f}" if pd.notna(x) else "—"
        )
    if "reward" in table:
        table["reward"] = table["reward"].apply(
            lambda x: f"£{x:+.2f}" if pd.notna(x) else "—"
        )
    cols = [c for c in [
        "interaction_id", "decision_at", "customer_id",
        "action", "converted", "revenue", "reward",
    ] if c in table.columns]
    st.dataframe(
        table[cols],
        hide_index=True,
        width="stretch",
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

# ── Auto-refresh ───────────────────────────────────────────────
if auto_refresh:
    time.sleep(30)
    bu.get_metrics.clear()
    st.rerun()