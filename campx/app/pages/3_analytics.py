"""
Page 3 — Performance
Owner: Armine Babajanyan (frontend branch)
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(page_title="Performance · CampX", layout="wide")
bu.render_global_navigation()

st.title("Performance")
st.caption("Campaign value, action mix, and segment-level outcomes.")
bu.render_reward_note()

sim_id, sims = bu.select_simulation_widget(key="analytics_sim")
if sim_id is None:
    st.info("No campaign runs yet. Launch one on **Campaign Setup**.")
    st.stop()

try:
    metrics = bu.get_metrics(sim_id)
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total rounds", f"{metrics['rounds_completed']:,}")
k2.metric("Cumulative reward", bu.format_currency(metrics["cumulative_reward"], round_int=True))
k3.metric("Avg reward / round", f"£{metrics['avg_reward_per_round']:.2f}" if metrics.get("avg_reward_per_round") is not None else "—")
k4.metric("Conversions", f"{metrics['conversions']:,}")
st.write("")

# ── Cumulative reward chart ────────────────────────────────────
st.subheader("Campaign value over time")
cum = metrics.get("cumulative_reward_series")
if cum is not None and not cum.empty:
    chart_df = cum.copy()
    if "round" in chart_df.columns:
        chart_df = chart_df.set_index("round")
    if "linucb" in chart_df.columns:
        chart_df = chart_df.rename(columns={"linucb": "CampX policy"})
    else:
        chart_df.columns = ["CampX policy"] if len(chart_df.columns) == 1 else chart_df.columns

    try:
        baselines = bu.get_baselines()
        if baselines:
            base_len = min(len(chart_df), len(baselines))
            chart_df = chart_df.iloc[:base_len].copy()
            chart_df["Random baseline"] = baselines[:base_len]
    except Exception:
        pass

    # Keep only the two primary curves; extra baselines go in the expander below.
    keep_cols = [c for c in ["CampX policy", "Random baseline"] if c in chart_df.columns]
    chart_df = chart_df[keep_cols]

    color_map = {
        "CampX policy": "#0f766e",      # teal
        "Random baseline": "#374151",   # dark gray, visible but professional
    }
    colors = [color_map.get(col, "#2563eb") for col in chart_df.columns]
    st.line_chart(chart_df, height=380, color=colors)
    st.caption(
        "Campaign value is cumulative simulated net reward: realized revenue minus promotional action cost. "
        "The random baseline is shown as a reference policy over the same action set."
    )
else:
    st.info("Cumulative reward chart will appear once `/metrics` returns the cumulative reward series.")

st.write("")

# ── Conversion/action summaries ────────────────────────────────
conv_raw = metrics.get("conversion_by_action")
conv = pd.DataFrame()
if conv_raw is not None and not conv_raw.empty:
    conv = conv_raw.copy()
    conv["label"] = conv["action"].map(bu.ACTION_LABELS).fillna(conv["action"])
    conv["cost"] = conv["action"].map(bu.ACTION_COSTS).fillna(0.0)

    if "avg_reward_per_pull" in conv.columns:
        conv["value_metric"] = conv["avg_reward_per_pull"]
        value_label = "Avg reward / pull"
    elif "est_reward_per_pull" in conv.columns:
        conv["value_metric"] = conv["est_reward_per_pull"]
        value_label = "Est. reward / pull"
    else:
        conv["value_metric"] = conv["conversion_rate"] * 65 - conv["cost"]
        value_label = "Est. reward / pull"
else:
    value_label = "Est. reward / pull"

# Policy summary is computed from the selected simulation's /metrics response, not static placeholder text.
st.subheader("Policy summary")
st.caption("Metrics shown for the selected campaign run. Reward is simulated revenue minus promotional action cost.")
if conv.empty:
    st.info("Policy summary is unavailable until `/metrics` returns `conversion_by_action`.")
else:
    best_value = conv.sort_values("value_metric", ascending=False).iloc[0]
    best_conversion = conv.sort_values("conversion_rate", ascending=False).iloc[0]
    dist_raw = metrics.get("action_distribution")
    most_selected = None
    if dist_raw is not None and not dist_raw.empty and "action" in dist_raw:
        most_selected = dist_raw["action"].value_counts().idxmax()
    most_selected_label = bu.ACTION_LABELS.get(most_selected, most_selected) if most_selected else "—"

    st.info(
        f"• **Highest observed net value:** {best_value['label']} ({bu.format_currency(best_value['value_metric'])} per pull)  \n"
        f"• **Highest conversion rate:** {best_conversion['label']} ({bu.format_pct(best_conversion['conversion_rate'])})  \n"
        f"• **Most selected action in this run:** {most_selected_label}"
    )

    st.success(
        f"**Highest observed net value action:** {best_value['label']} · "
        f"{value_label.lower()} {bu.format_currency(best_value['value_metric'])} · "
        f"{int(best_value['n_pulls'])} pulls"
    )

st.write("")

# ── Action distribution + conversion ───────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Action distribution")
    st.caption("Which promotional actions the policy selected.")
    dist_raw = metrics.get("action_distribution")
    if dist_raw is None or dist_raw.empty:
        st.info("Awaiting `action_distribution` from `/metrics`.")
    else:
        counts = dist_raw["action"].value_counts().rename_axis("action").reset_index(name="count")
        counts["Action"] = counts["action"].map(bu.ACTION_LABELS).fillna(counts["action"])
        chart = counts.set_index("Action")[["count"]]
        st.bar_chart(chart, height=360, color="#0f766e")

with right:
    st.subheader("Conversion rate by action")
    st.caption("Response rate by promotional action.")
    if conv.empty:
        st.info("Awaiting `conversion_by_action` from `/metrics`.")
    else:
        conv_chart = conv.set_index("label")[["conversion_rate"]]
        st.bar_chart(conv_chart, height=360, color="#2563eb")

st.write("")

# ── Detailed results table ────────────────────────────────────
st.subheader("Per-action detail")
if conv.empty:
    st.info("Awaiting `conversion_by_action` from `/metrics`.")
else:
    detail = conv[["label", "n_pulls", "conversion_rate", "cost", "value_metric"]].copy()
    detail["conversion_rate"] = detail["conversion_rate"].map(bu.format_pct)
    detail["cost"] = detail["cost"].map(bu.format_currency)
    detail["value_metric"] = detail["value_metric"].map(lambda x: f"£{x:+.2f}" if pd.notna(x) else "—")
    st.dataframe(
        detail,
        hide_index=True,
        width="stretch",
        column_config={
            "label": "Action",
            "n_pulls": "Pulls",
            "conversion_rate": "Conversion",
            "cost": "Cost",
            "value_metric": value_label,
        },
    )

st.write("")

# ── Segment-level performance ──────────────────────────────────
st.subheader("Segment performance")
st.caption("Best observed action per customer segment in the selected run.")
with st.expander("How segments are defined"):
    for segment, definition in bu.SEGMENT_DEFINITIONS.items():
        st.write(f"**{segment}:** {definition}")

ALL_SEGMENTS = ["Champion", "Loyal", "At-Risk", "Lost"]
seg_perf = metrics.get("segment_performance")
if seg_perf is None or seg_perf.empty:
    st.info("Segment performance will appear once interactions are recorded.")
else:
    seg_action = seg_perf.copy()
    if "action_label" in seg_action.columns:
        seg_action["action_label"] = seg_action["action_label"].map(bu.ACTION_LABELS).fillna(seg_action["action_label"])
    seg_action["conversion_rate"] = seg_action["conversions"] / seg_action["pulls"]

    if "avg_reward" in seg_action.columns:
        best = seg_action.sort_values(["avg_reward", "pulls"], ascending=[False, False]).groupby("segment_label").first().reset_index()
    else:
        best = seg_action.sort_values(["conversion_rate", "pulls"], ascending=[False, False]).groupby("segment_label").first().reset_index()

    all_seg = pd.DataFrame({"segment_label": ALL_SEGMENTS})
    best = all_seg.merge(best, on="segment_label", how="left")
    best["action_label"] = best["action_label"].fillna("—")
    best["pulls"] = best["pulls"].fillna(0).astype(int)
    best["conversions"] = best["conversions"].fillna(0).astype(int)
    best["conversion_rate"] = best["conversion_rate"].apply(lambda x: bu.format_pct(x) if pd.notna(x) else "—")
    
    if "avg_reward" in best.columns:
        best["avg_reward"] = best["avg_reward"].apply(lambda x: f"£{x:+.2f}" if pd.notna(x) else "—")
        show_cols = ["segment_label", "action_label", "pulls", "conversions", "conversion_rate", "avg_reward"]
        col_cfg = {"avg_reward": "Avg reward"}
    else:
        show_cols = ["segment_label", "action_label", "pulls", "conversions", "conversion_rate"]
        col_cfg = {}

    col_cfg.update({
        "segment_label": "Segment",
        "action_label": "Best action",
        "pulls": "Pulls",
        "conversions": "Conversions",
        "conversion_rate": "Conversion rate",
    })
    st.dataframe(best[show_cols], hide_index=True, width="stretch", column_config=col_cfg)
