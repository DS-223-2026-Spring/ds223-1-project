"""
Page 3 — Analytics
Owner: Armine Babajanyan (frontend branch)

Result analysis: champion action, action distribution,
conversion rate per action, policy comparison.
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(page_title="Analytics · CampX", layout="wide")
bu.render_global_navigation()


st.title("Analytics")
st.caption("Results, action distributions, and policy comparison.")

# ── Simulation selector ────────────────────────────────────────
sim_id, sims = bu.select_simulation_widget(key="analytics_sim")
if sim_id is None:
    st.info("No simulations yet. Launch one on **Create Simulation**.")
    st.stop()

# ── Fetch metrics ──────────────────────────────────────────────
try:
    metrics = bu.get_metrics(sim_id)
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

# ── Summary tiles (always available) ───────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total rounds", f"{metrics['rounds_completed']:,}")
k2.metric("Cumulative reward",
          bu.format_currency(metrics["cumulative_reward"]))
k3.metric("Avg reward / round",
          f"£{metrics['avg_reward_per_round']:.2f}" if metrics.get("avg_reward_per_round") is not None else "—")
k4.metric("Conversions", f"{metrics['conversions']:,}")
st.write("")

# ── Cumulative reward chart ────────────────────────────────────
st.subheader("LinUCB cumulative reward over 5,000 rounds")
cum = metrics.get("cumulative_reward_series")
if cum is not None and not cum.empty:
    chart_df = cum.copy()
    if "round" in chart_df.columns:
        chart_df = chart_df.set_index("round")
    if "linucb" in chart_df.columns:
        chart_df = chart_df.rename(columns={"linucb": "LinUCB"})
    else:
        chart_df.columns = ["LinUCB"] if len(chart_df.columns) == 1 else chart_df.columns
    
    # Load random baseline and merge
    try:
        baselines = bu.get_baselines()
        if baselines:
            base_len = min(len(chart_df), len(baselines))
            chart_df = chart_df.iloc[:base_len].copy()
            chart_df["Random baseline"] = baselines[:base_len]
    except Exception:
        pass
    
    colors = ["#0f766e", "#cbd5e1"][:len(chart_df.columns)]
    st.line_chart(
        chart_df,
        height=380,
        color=colors
    )

st.write("")

# ── What the model learned ─────────────────────────────────────
st.subheader("What the model learned")
conv_raw = metrics.get("conversion_by_action")
if conv_raw is not None and not conv_raw.empty:
    conv = conv_raw.copy()
    conv["label"] = conv["action"].map(bu.ACTION_LABELS).fillna(conv["action"])
    conv["cost"] = conv["action"].map(bu.ACTION_COSTS).fillna(0.0)
    conv["est_reward_per_pull"] = conv["conversion_rate"] * 65 - conv["cost"]
    champion = conv.sort_values("est_reward_per_pull", ascending=False).iloc[0]
    
    dist_raw = metrics.get("action_distribution")
    most_explored = dist_raw["action"].value_counts().idxmax() if (dist_raw is not None and not dist_raw.empty) else champion["action"]
    most_explored_label = bu.ACTION_LABELS.get(most_explored, most_explored)
    
    # We can fetch segment best actions from the segment performance data
    ri = metrics.get("recent_interactions")
    champion_action = "—"
    at_risk_action = "—"
    if ri is not None and not ri.empty:
        try:
            customers = bu.list_customers()
            if not customers.empty and "segment_label" in customers.columns:
                seg_df = ri.merge(customers[["customer_id", "segment_label"]], on="customer_id", how="left")
                seg_df["action_label"] = seg_df["action"].map(bu.ACTION_LABELS).fillna(seg_df["action"])
                seg_action = seg_df.groupby(["segment_label", "action_label"]).agg(
                    pulls=("customer_id", "size"),
                    conversions=("converted", lambda x: x.sum() if x.notna().any() else 0),
                ).reset_index()
                seg_action["conversion_rate"] = seg_action["conversions"] / seg_action["pulls"]
                best = seg_action.sort_values(["conversion_rate", "pulls"], ascending=[False, False]).groupby("segment_label").first()
                if "Champion" in best.index:
                    champion_action = f"{best.loc['Champion', 'action_label']} ({bu.format_pct(best.loc['Champion', 'conversion_rate'])})"
                if "At-Risk" in best.index:
                    at_risk_action = f"{best.loc['At-Risk', 'action_label']} ({bu.format_pct(best.loc['At-Risk', 'conversion_rate'])})"
        except Exception:
            pass
            
    st.info(
        "• **Champions:** " + champion_action + " \n"
        "• **At-Risk:** " + at_risk_action + " \n"
        "• **Highest overall converting:** " + f"{champion['label']} ({bu.format_pct(champion['conversion_rate'])})" + " \n"
        "• **Most explored:** " + f"{most_explored_label}"
    )

st.write("")

# ── Headline: champion action ──────────────────────────────────
conv_raw = metrics.get("conversion_by_action")
if conv_raw is None or conv_raw.empty:
    st.info(
        "Champion-action analysis is unavailable until `/metrics` returns "
        "the `conversion_by_action` array."
    )
    conv = pd.DataFrame()
else:
    conv = conv_raw.copy()
    conv["label"] = conv["action"].map(bu.ACTION_LABELS).fillna(conv["action"])
    conv["cost"] = conv["action"].map(bu.ACTION_COSTS).fillna(0.0)
    # Approximate reward potential per pull (avg basket × conv − cost)
    conv["est_reward_per_pull"] = conv["conversion_rate"] * 65 - conv["cost"]
    champion = conv.sort_values("est_reward_per_pull", ascending=False).iloc[0]
    st.success(
        f"**Champion action:** {champion['label']}  ·  "
        f"conversion rate {bu.format_pct(champion['conversion_rate'])}  ·  "
        f"{int(champion['n_pulls'])} pulls"
    )

# ── Action distribution + conversion ───────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Action distribution")
    st.caption("Which arm LinUCB chose, and how often.")
    dist_raw = metrics.get("action_distribution")
    if dist_raw is None or dist_raw.empty:
        st.info("Awaiting `action_distribution` from `/metrics`.")
    else:
        counts = dist_raw["action"].value_counts().rename_axis("action").reset_index(name="count")
        counts["Action"] = counts["action"].map(bu.ACTION_LABELS).fillna(counts["action"])
        chart = counts.set_index("Action")[["count"]]
        st.bar_chart(
            chart,
            height=380,
            color="#0f766e"
        )

with right:
    st.subheader("Conversion rate by action")
    st.caption("Did the action actually win the customer?")
    if conv.empty:
        st.info("Awaiting `conversion_by_action` from `/metrics`.")
    else:
        conv_chart = conv.set_index("label")[["conversion_rate"]]
        st.bar_chart(
            conv_chart,
            height=380,
            color="#3b82f6"
        )

st.write("")

# ── Detailed results table ────────────────────────────────────
st.subheader("Per-action detail")
if conv.empty:
    st.info("Awaiting `conversion_by_action` from `/metrics`.")
else:
    detail = conv[["label", "n_pulls", "conversion_rate", "cost",
                   "est_reward_per_pull"]].copy()
    detail["conversion_rate"] = detail["conversion_rate"].map(bu.format_pct)
    detail["cost"] = detail["cost"].map(bu.format_currency)
    detail["est_reward_per_pull"] = detail["est_reward_per_pull"].map(
        lambda x: f"£{x:+.2f}"
    )
    st.dataframe(
        detail, hide_index=True, width="stretch",
        column_config={
            "label": "Action",
            "n_pulls": "Pulls",
            "conversion_rate": "Conversion",
            "cost": "Cost",
            "est_reward_per_pull": "Est. reward/pull",
        },
    )

st.write("")

# ── Segment-level performance ──────────────────────────────────
st.subheader("Segment performance")
st.caption(
    "Best-performing action per customer segment. "
)

ALL_SEGMENTS = ["Champion", "Loyal", "At-Risk", "Lost"]

ri = metrics.get("recent_interactions")
if ri is None or ri.empty:
    st.info("Segment performance will appear once interactions are recorded.")
else:
    try:
        customers = bu.list_customers()
        if not customers.empty and "segment_label" in customers.columns:
            # Join interactions with customer segments
            seg_df = ri.merge(
                customers[["customer_id", "segment_label"]],
                on="customer_id",
                how="left",
            )
            if "action" in seg_df.columns and "segment_label" in seg_df.columns:
                seg_df["action_label"] = seg_df["action"].map(bu.ACTION_LABELS).fillna(seg_df["action"])
                # Compute per-segment per-action conversion rates
                seg_action = (
                    seg_df.groupby(["segment_label", "action_label"])
                    .agg(
                        pulls=("customer_id", "size"),
                        conversions=("converted", lambda x: x.sum() if x.notna().any() else 0),
                    )
                    .reset_index()
                )
                seg_action["conversion_rate"] = seg_action["conversions"] / seg_action["pulls"]
                # Pick best action per segment (highest conversion rate, break ties by pulls)
                best = (
                    seg_action.sort_values(
                        ["conversion_rate", "pulls"], ascending=[False, False]
                    )
                    .groupby("segment_label")
                    .first()
                    .reset_index()
                )
                # Ensure all 4 segments appear
                all_seg = pd.DataFrame({"segment_label": ALL_SEGMENTS})
                best = all_seg.merge(best, on="segment_label", how="left")
                best["action_label"] = best["action_label"].fillna("—")
                best["pulls"] = best["pulls"].fillna(0).astype(int)
                best["conversions"] = best["conversions"].fillna(0).astype(int)
                best["conversion_rate"] = best["conversion_rate"].apply(
                    lambda x: bu.format_pct(x) if pd.notna(x) else "—"
                )
                st.dataframe(
                    best[["segment_label", "action_label", "pulls", "conversions", "conversion_rate"]],
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "segment_label": "Segment",
                        "action_label": "Best action",
                        "pulls": "Pulls",
                        "conversions": "Conversions",
                        "conversion_rate": "Conversion rate",
                    },
                )
            else:
                st.info("Segment data not available in interactions.")
        else:
            st.info("No customer data available for segment analysis.")
    except bu.APIError:
        st.info("Could not load customer data for segment analysis.")