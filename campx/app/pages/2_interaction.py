"""
Page 2 — Live Decisions
Owner: Armine Babajanyan (frontend branch)
"""
import time

import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(page_title="Live Decisions · CampX", layout="wide")
bu.render_global_navigation()

st.title("Live Decisions")
st.caption("Monitor customer-level promotion decisions and reward feedback as the policy updates.")
bu.render_reward_note()

sim_id, sims = bu.select_simulation_widget(key="interaction_sim")
if sim_id is None:
    st.info("No campaign runs yet. Launch one on **Campaign Setup**.")
    st.stop()

c1, c2 = st.columns([1, 1])
with c1:
    auto_refresh = st.toggle("Auto-refresh every 30 seconds", value=False)
with c2:
    if st.button("Refresh now"):
        bu.get_metrics.clear()
        bu.get_model_state.clear()
        st.rerun()

try:
    metrics = bu.get_metrics(sim_id)
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Rounds completed", f"{metrics['rounds_completed']:,}")
k2.metric("Cumulative reward", bu.format_currency(metrics["cumulative_reward"], round_int=True))
k3.metric("Avg reward / round", f"£{metrics['avg_reward_per_round']:.2f}" if metrics.get("avg_reward_per_round") is not None else "—")
pending = metrics.get("pending_observations")
k4.metric("Pending observations", "—" if pending is None else f"{pending:,}", help="Interactions still inside the conversion window.")

k5, k6, k7, k8 = st.columns(4)
k5.metric("Conversions", f"{metrics['conversions']:,}")
k6.metric("Total revenue", bu.format_currency(metrics["total_revenue"], round_int=True))
k7.metric("Total cost", bu.format_currency(metrics["total_cost"]))
conv_rate = metrics["conversions"] / metrics["rounds_completed"] if metrics["rounds_completed"] else 0.0
k8.metric("Overall conversion rate", bu.format_pct(conv_rate))

st.write("")

cum = metrics.get("cumulative_reward_series")
st.subheader("Reward per round")
st.caption("Per-round reward and rolling average. A stable upward cumulative trend means the policy is collecting value over the run.")
if cum is None or cum.empty:
    st.info("Reward-per-round chart will appear once the cumulative reward series is available from `/metrics`.")
else:
    rpr = cum.copy()
    if "round" in rpr.columns:
        rpr = rpr.set_index("round")
    col = rpr.columns[0]
    rpr["Per round"] = rpr[col].diff().fillna(rpr[col])
    window = max(1, len(rpr) // 20)
    rpr["Rolling avg"] = rpr["Per round"].rolling(window, min_periods=1).mean()
    st.line_chart(rpr[["Per round", "Rolling avg"]], height=320, color=["#cbd5e1", "#0f766e"])

st.write("")

st.subheader("Action selection over time")
st.caption("Which promotional action was selected in each part of the run.")
dist = metrics.get("action_distribution")
if dist is None or dist.empty:
    st.info("Action distribution will appear once the backend returns the `action_distribution` array.")
else:
    df = dist.copy()
    if "round" in df.columns:
        df["bucket"] = (df["round"] // 100) * 100
    else:
        df["bucket"] = df.index // 100 * 100
    counts = df.groupby(["bucket", "action"]).size().unstack(fill_value=0).sort_index()
    counts.columns = [bu.ACTION_LABELS.get(c, c) for c in counts.columns]
    st.area_chart(counts, height=320, stack=True, x_label="Round (binned by 100)", y_label="Times chosen")

    total = counts.sum().sum()
    if total:
        top_share = counts.sum().max() / total
        if top_share > 0.95 and len(counts.columns) > 1:
            st.caption("Note: this run is strongly concentrated in one action. For live demos, prefer a run with warm-start exploration enabled.")

st.write("")

st.subheader("Recent decision history")
ri = metrics.get("recent_interactions")
if ri is None or ri.empty:
    st.info("Recent interactions will appear once the backend returns the `recent_interactions` array.")
else:
    table = ri.copy()
    if "action" in table:
        table["action"] = table["action"].map(lambda a: bu.ACTION_LABELS.get(a, a))
    if "decision_at" in table:
        table["decision_at"] = table["decision_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    if "revenue" in table:
        table["revenue"] = table["revenue"].apply(lambda x: f"£{x:.2f}" if pd.notna(x) else "—")
    if "reward" in table:
        table["reward"] = table["reward"].apply(lambda x: f"£{x:+.2f}" if pd.notna(x) else "—")
    cols = [c for c in ["interaction_id", "decision_at", "customer_id", "action", "converted", "revenue", "reward"] if c in table.columns]
    st.dataframe(table[cols], hide_index=True, width="stretch", column_config={
        "interaction_id": "ID",
        "decision_at": "Time",
        "customer_id": "Customer",
        "action": "Action",
        "converted": "Converted",
        "revenue": "Revenue",
        "reward": "Reward",
    })

if auto_refresh:
    time.sleep(30)
    bu.get_metrics.clear()
    st.rerun()
