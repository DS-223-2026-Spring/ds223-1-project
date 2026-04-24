"""
Page 4 — Model Inspector
Owner: Armine Babajanyan (frontend branch)

An extra page beyond the instructor's 3-page structure — justified because
LinUCB has richer internals than a Bayesian bandit: a 6×5 θ matrix, per-arm
covariance, and a decomposable UCB score. Academically useful for showing
WHAT the model learned, not just its outputs.

M2: θ heatmap, n_pulls bars, UCB decomposition layout with mock data.
M3: Connect to GET /model/state and POST /decide?preview=true (no write).

Backend endpoints consumed:
  GET  /simulations                        : simulation selector
  GET  /model/state?simulation_id=...      : θ matrix + n_pulls + α
  POST /decide?customer_id=...&preview=true: per-action UCB breakdown
"""
import pandas as pd
import plotly.express as px
import streamlit as st

import bandit_utils as bu

st.set_page_config(
    page_title="Model · CampX",
    layout="wide",
)

st.title("Model Inspector")
st.caption(
    "What LinUCB has learned — θ vectors, pull counts, UCB decomposition."
)

# ── Simulation selector ────────────────────────────────────────
sim_id, sims = bu.select_simulation_widget(key="model_sim")
if sim_id is None:
    st.info("No simulations yet. Launch one on **Create Simulation**.")
    st.stop()

state = bu.get_model_state(sim_id)
st.metric("Alpha (exploration)", f"{state['alpha']:.2f}")

st.divider()

# ── Theta heatmap ──────────────────────────────────────────────
st.subheader("θ heatmap — learned feature weights per action")
st.caption(
    "Rows are RFM features, columns are actions. Red = positive weight, "
    "blue = negative. If LinUCB learned, you should see meaningful "
    "structure — not noise."
)

theta = state["theta"]
theta_display = theta.rename(columns=bu.ACTION_LABELS)
fig_t = px.imshow(
    theta_display,
    color_continuous_scale="RdBu_r",
    zmin=-1.5, zmax=1.5,
    aspect="auto",
    text_auto=".2f",
)
fig_t.update_layout(
    height=400,
    xaxis_title=None,
    yaxis_title=None,
    margin=dict(t=20, b=20),
)
st.plotly_chart(fig_t, width='stretch')

st.divider()

# ── n_pulls bars ───────────────────────────────────────────────
st.subheader("Pull counts per action")
st.caption("How often each arm was chosen. Watch for convergence.")

pulls_df = pd.DataFrame([
    {"action": k, "label": bu.ACTION_LABELS[k], "n_pulls": v}
    for k, v in state["n_pulls"].items()
])
fig_p = px.bar(
    pulls_df, x="label", y="n_pulls", color="action",
    color_discrete_map=bu.ACTION_COLORS,
    labels={"label": "Action", "n_pulls": "Times chosen"},
)
fig_p.update_layout(
    showlegend=False, height=350, margin=dict(t=20, b=20),
)
st.plotly_chart(fig_p, width='stretch')

st.divider()

# ── UCB decomposition for a specific customer ──────────────────
st.subheader("UCB decomposition — predict for a customer")
st.caption(
    "For any customer, show the exploit term (θᵀx), the explore bonus "
    "(α·√(xᵀA⁻¹x)), and which action wins."
)

c1, c2 = st.columns([1, 3])
with c1:
    cid = st.number_input(
        "Customer ID", min_value=1, max_value=500, value=1, step=1,
    )
    predict_clicked = st.button(
        "🎯 Predict", type="primary", width='stretch',
    )

with c2:
    if predict_clicked:
        breakdown = bu.predict_for_customer(int(cid))
        breakdown["action_label"] = breakdown["action"].map(bu.ACTION_LABELS)

        chosen = breakdown.iloc[0]
        st.success(
            f"**Chosen action: {chosen['action_label']}**  ·  "
            f"UCB = {chosen['ucb_score']:.3f}  ·  "
            f"cost {chosen['cost']:.2f}"
        )

        long = breakdown.melt(
            id_vars="action_label",
            value_vars=["exploit", "explore"],
            var_name="component",
            value_name="score",
        )
        fig_u = px.bar(
            long.sort_values("action_label"),
            x="score", y="action_label", color="component",
            orientation="h",
            color_discrete_map={"exploit": "#1F2937", "explore": "#9CA3AF"},
            labels={"action_label": "Action", "score": "UCB score"},
        )
        fig_u.update_layout(
            barmode="stack", height=320,
            legend_title_text=None, margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig_u, width='stretch')

        with st.expander("Raw per-action scores"):
            st.dataframe(
                breakdown, hide_index=True, width='stretch',
            )
    else:
        st.info(
            "Pick a customer ID and click **Predict** to see the "
            "per-action UCB breakdown."
        )

st.caption("M2: scores from mock generator. Real θ and A⁻¹ wired in M3.")