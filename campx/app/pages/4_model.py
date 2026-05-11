"""
Page 4 — Model Inspector
Owner: Armine Babajanyan (frontend branch)

What LinUCB has learned: θ matrix, pull counts, UCB decomposition.

Wired to:
  GET  /simulations
  GET  /model/state?simulation_id=...
  POST /decide?customer_id=...&simulation_id=...&preview=true

Built-in Streamlit components only:
  - θ heatmap is a styled DataFrame (pandas Styler + st.dataframe)
  - bar charts use st.bar_chart
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(page_title="Model · CampX", layout="wide")

st.title("Model Inspector")
st.caption("What LinUCB has learned — θ vectors, pull counts, UCB decomposition.")

# ── Simulation selector ────────────────────────────────────────
sim_id, sims = bu.select_simulation_widget(key="model_sim")
if sim_id is None:
    st.info("No simulations yet. Launch one on **Create Simulation**.")
    st.stop()

# ── Fetch model state ──────────────────────────────────────────
try:
    state = bu.get_model_state(sim_id)
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Alpha (exploration)", f"{state['alpha']:.2f}")
m2.metric("Round number", f"{state['round_number']:,}")
m3.metric("Total pulls", f"{sum(state['n_pulls'].values()):,}")

st.divider()

# ── Theta matrix (heatmap-style via pandas Styler) ─────────────
st.subheader("θ matrix — learned feature weights per action")
st.caption(
    "Rows: RFM features. Columns: actions. Higher (red) = positive weight; "
    "lower (blue) = negative. Real structure means LinUCB learned something."
)

theta = state["theta"].copy()
# Display friendly action labels
theta.columns = [bu.ACTION_LABELS.get(c, c) for c in theta.columns]


theta_max_abs = max(1e-6, float(theta.abs().max().max()))

def _theta_cell_style(val) -> str:
    """Red-for-positive, blue-for-negative cell shading via inline CSS."""
    if val is None or pd.isna(val):
        return ""
    v = float(val) / theta_max_abs  # → [-1, 1]
    if v >= 0:
        # Toward red: blend white (255,255,255) → red (239, 68, 68)
        r = int(255 - (255 - 239) * v)
        g = int(255 - (255 - 68) * v)
        b = int(255 - (255 - 68) * v)
    else:
        # Toward blue: blend white (255,255,255) → blue (59, 130, 246)
        v = -v
        r = int(255 - (255 - 59) * v)
        g = int(255 - (255 - 130) * v)
        b = int(255 - (255 - 246) * v)
    text_color = "white" if abs(v) > 0.55 else "#1F2937"
    return f"background-color: rgb({r},{g},{b}); color: {text_color};"


styled_theta = theta.style.map(_theta_cell_style).format("{:.3f}")
st.dataframe(styled_theta, width="stretch")

st.divider()

# ── n_pulls bars ───────────────────────────────────────────────
st.subheader("Pull counts per action")
st.caption("How often each arm was chosen. Watch for convergence.")

pulls_df = pd.DataFrame([
    {"Action": bu.ACTION_LABELS.get(k, k), "Times chosen": v}
    for k, v in state["n_pulls"].items()
]).set_index("Action")
st.bar_chart(pulls_df, height=320, y_label="Times chosen")

st.divider()

# ── UCB decomposition for one customer ─────────────────────────
st.subheader("UCB decomposition — predict for a customer")
st.caption(
    "For any customer, show the exploit term and the explore bonus, and which action wins."
)

c1, c2 = st.columns([1, 3])
with c1:
    cid = st.number_input(
        "Customer ID", min_value=1, max_value=10000, value=1, step=1,
    )
    predict_clicked = st.button(
        "🎯 Predict", type="primary", width="stretch",
    )

with c2:
    if predict_clicked:
        try:
            breakdown = bu.predict_for_customer(sim_id, int(cid))
        except bu.APIError as exc:
            bu.render_api_error(exc)
            breakdown = pd.DataFrame()

        if breakdown.empty:
            st.warning("No scores returned for that customer.")
        else:
            breakdown["action_label"] = (
                breakdown["action"].map(bu.ACTION_LABELS).fillna(breakdown["action"])
            )
            chosen = breakdown.iloc[0]
            st.success(
                f"**Chosen action: {chosen['action_label']}**  ·  "
                f"UCB = {chosen['ucb_score']:.3f}  ·  "
                f"cost {bu.format_currency(chosen['cost'])}"
            )

            # Stacked horizontal bar: exploit + explore per action
            chart_df = breakdown.set_index("action_label")[["exploit", "explore"]]
            st.bar_chart(
                chart_df,
                horizontal=True,
                stack=True,
                height=320,
                x_label="UCB score",
            )

            with st.expander("Raw per-action scores"):
                detail = breakdown[[
                    "action_label", "exploit", "explore", "ucb_score", "cost",
                ]].rename(columns={
                    "action_label": "Action",
                    "exploit": "Exploit",
                    "explore": "Explore",
                    "ucb_score": "UCB",
                    "cost": "Cost",
                })
                st.dataframe(detail, hide_index=True, width="stretch")
    else:
        st.info(
            "Pick a customer ID and click **Predict** to see the "
            "per-action UCB breakdown."
        )