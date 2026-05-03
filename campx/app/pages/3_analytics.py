"""
Page 3 — Analytics
Owner: Armine Babajanyan (frontend branch)

The summary / results page — for interpreting what a simulation produced.
  - champion action (highest cumulative reward)
  - action distribution
  - conversion rate per action
  - cumulative reward curve for completed runs

M2: Layout + charts with mock data.
M3: Connect to GET /metrics, GET /customers for filtering by segment.

Backend endpoints consumed:
  GET /simulations                  : selector
  GET /metrics?simulation_id=...    : aggregates
"""
import pandas as pd
import plotly.express as px
import streamlit as st

import bandit_utils as bu

st.set_page_config(
    page_title="Analytics · CampX",
    layout="wide",
)

st.title("Analytics")
st.caption("Results, action distributions, and policy comparison.")

# ── Simulation selector ────────────────────────────────────────
sim_id, sims = bu.select_simulation_widget(key="analytics_sim")
if sim_id is None:
    st.info("No simulations yet. Launch one on **Create Simulation**.")
    st.stop()

metrics = bu.get_metrics(sim_id)

# ── Headline: champion action ──────────────────────────────────
conv = metrics["conversion_by_action"].copy()
conv["label"] = conv["action"].map(bu.ACTION_LABELS)
conv["cost"] = conv["action"].map(bu.ACTION_COSTS)
# approximate reward potential per pull
conv["est_reward_per_pull"] = conv["conversion_rate"] * 65 - conv["cost"]

champion = conv.sort_values("est_reward_per_pull", ascending=False).iloc[0]

st.success(
    f"**Champion action:** {champion['label']}  ·  "
    f"conversion rate {bu.format_pct(champion['conversion_rate'])}  ·  "
    f"{int(champion['n_pulls'])} pulls"
)

# ── Summary tiles ──────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total rounds", f"{metrics['rounds_completed']:,}")
k2.metric("Cumulative reward",
          bu.format_currency(metrics["cumulative_reward"]))
k3.metric("Avg reward / round",
          f"£{metrics['avg_reward_per_round']:.2f}")
k4.metric("Pending observations", metrics["pending_observations"])

st.divider()

# ── Action distribution + conversion ───────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Action distribution")
    st.caption("Which arm LinUCB chose, and how often.")
    dist = metrics["action_distribution"]
    counts = dist["action"].value_counts().reset_index()
    counts.columns = ["action", "count"]
    counts["label"] = counts["action"].map(bu.ACTION_LABELS)
    fig_d = px.bar(
        counts, x="label", y="count",
        labels={"label": "Action", "count": "Times chosen"},
    )
    fig_d.update_traces(marker_color="#6495ED")  # single muted slate
    fig_d.update_layout(
        showlegend=False, height=380,
        margin=dict(t=20, b=20),
        plot_bgcolor="white",
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig_d, width='stretch')
    st.caption("M3: upgrade to stacked-area over time.")

with right:
    st.subheader("Conversion rate by action")
    st.caption("Did the action actually win the customer?")
    fig_c = px.bar(
        conv, x="label", y="conversion_rate",
        labels={"label": "Action", "conversion_rate": "Conversion rate"},
    )
    fig_c.update_traces(marker_color="#6495ED")
    fig_c.update_layout(
        showlegend=False, height=380,
        yaxis_tickformat=".0%",
        margin=dict(t=20, b=20),
        plot_bgcolor="white",
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig_c, width='stretch')

st.divider()

# ── Policy comparison ──────────────────────────────────────────
st.subheader("Policy comparison — LinUCB vs baselines")
st.caption(
    "Cumulative reward over time. LinUCB should pull ahead as it learns; "
    "Random and Heuristic represent zero-intelligence and static-rule "
    "baselines."
)

cum = metrics["cumulative_reward_series"]
finals = pd.DataFrame({
    "Policy": ["LinUCB", "Heuristic", "Random"],
    "Final cumulative reward": [
        cum["linucb"].iloc[-1],
        cum["heuristic"].iloc[-1],
        cum["random"].iloc[-1],
    ],
})
fig_f = px.bar(
    finals, x="Policy", y="Final cumulative reward",
)
fig_f.update_traces(marker_color="#6495ED")
fig_f.update_layout(
    showlegend=False, height=320, yaxis_title="£",
    margin=dict(t=20, b=20),
    plot_bgcolor="white",
    yaxis=dict(showgrid=False),
    xaxis=dict(showgrid=False),
)
st.plotly_chart(fig_f, width='stretch')

st.divider()

# ── Detailed results table ────────────────────────────────────
st.subheader("Per-action detail")
detail = conv[["label", "n_pulls", "conversion_rate", "cost",
               "est_reward_per_pull"]].copy()
detail["conversion_rate"] = detail["conversion_rate"].map(bu.format_pct)
detail["cost"] = detail["cost"].map(bu.format_currency)
detail["est_reward_per_pull"] = detail["est_reward_per_pull"].map(
    lambda x: f"£{x:+.2f}"
)
st.dataframe(
    detail, hide_index=True, width='stretch',
    column_config={
        "label": "Action",
        "n_pulls": "Pulls",
        "conversion_rate": "Conversion",
        "cost": "Cost",
        "est_reward_per_pull": "Est. reward/pull",
    },
)

st.caption("M2: mock data. Real computations wire in M3.")