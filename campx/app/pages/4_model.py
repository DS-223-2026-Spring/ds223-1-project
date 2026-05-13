"""
Page 4 — Decision Logic
Owner: Armine Babajanyan (frontend branch)
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(page_title="Decision Logic · CampX", layout="wide")
bu.render_global_navigation()

st.title("Decision Logic")
st.caption("Inspect how the policy scores actions using learned value and uncertainty.")

sim_id, sims = bu.select_simulation_widget(key="model_sim")
if sim_id is None:
    st.info("No campaign runs yet. Launch one on **Campaign Setup**.")
    st.stop()

try:
    state = bu.get_model_state(sim_id)
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Alpha: exploration", f"{state['alpha']:.2f}")
m2.metric("Round number", f"{state['round_number']:,}")
m3.metric("Total pulls", f"{sum(state['n_pulls'].values()):,}")

st.write("")

# ── Learned weights ───────────────────────────────────────────
st.subheader("Learned decision drivers")
st.caption(
    "Technical view: weights are learned on normalized RFM-style features. "
    "Warmer cells indicate stronger positive contribution to an action score; cooler cells indicate negative contribution."
)

theta = state["theta"].copy()
theta.columns = [bu.ACTION_LABELS.get(c, c) for c in theta.columns]
theta_max_abs = max(1e-6, float(theta.abs().max().max()))


def _theta_cell_style(val) -> str:
    if val is None or pd.isna(val):
        return ""
    v = float(val) / theta_max_abs
    base_r, base_g, base_b = 255, 255, 255
    if v >= 0:
        r = int(base_r + (239 - base_r) * v)
        g = int(base_g + (68 - base_g) * v)
        b = int(base_b + (68 - base_b) * v)
    else:
        v = -v
        r = int(base_r + (59 - base_r) * v)
        g = int(base_g + (130 - base_g) * v)
        b = int(base_b + (246 - base_b) * v)
    text_color = "white" if abs(v) > 0.55 else "#1f2937"
    return f"background-color: rgb({r},{g},{b}); color: {text_color};"


with st.expander("Technical model state: θ matrix", expanded=True):
    styled_theta = theta.style.map(_theta_cell_style).format("{:.3f}")
    st.dataframe(styled_theta, width="stretch")

st.write("")

# ── Pull counts ────────────────────────────────────────────────
st.subheader("Promotion selection volume")
st.caption("How often each action was selected. Strong concentration may indicate convergence or insufficient initial exploration.")

pulls_df = pd.DataFrame([
    {"Action": bu.ACTION_LABELS.get(k, k), "Times chosen": v}
    for k, v in state["n_pulls"].items()
]).set_index("Action")
st.bar_chart(pulls_df, height=320, color="#0f766e")

if pulls_df["Times chosen"].sum() > 0:
    top_share = pulls_df["Times chosen"].max() / pulls_df["Times chosen"].sum()
    if top_share > 0.95 and len(pulls_df[pulls_df["Times chosen"] > 0]) <= 2:
        st.caption("Note: this run is highly concentrated in one action. Use warm-start exploration for a cleaner demonstration of action coverage.")

st.write("")

# ── UCB decomposition ─────────────────────────────────────────
st.subheader("Action score breakdown for one customer")
st.caption(
    "For a selected customer, compare each action’s learned value and uncertainty bonus. "
    "The chosen action has the highest upper-confidence score."
)

c1, c2 = st.columns([1, 3])
with c1:
    cid = st.number_input("Customer ID", min_value=1, max_value=10000, value=1, step=1)
    predict_clicked = st.button("Predict action", type="primary", width="stretch")

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
            breakdown["action_label"] = breakdown["action"].map(bu.ACTION_LABELS).fillna(breakdown["action"])
            chosen = breakdown.iloc[0]
            st.success(
                f"**Recommended action:** {chosen['action_label']} · "
                f"UCB = {chosen['ucb_score']:.3f} · cost {bu.format_currency(chosen['cost'])}"
            )

            try:
                cust = bu.get_customer(int(cid))
                chosen_act = chosen["action"]
                act_theta = state["theta"][chosen_act]

                contribs = {}
                rfm = cust.get("rfm", {}) if isinstance(cust, dict) else {}
                for feat in act_theta.index:
                    source = rfm if feat in rfm else cust
                    if feat in source and feat != "intercept":
                        try:
                            val = float(source[feat])
                            contribs[feat] = act_theta[feat] * val
                        except (ValueError, TypeError):
                            pass

                if contribs:
                    sorted_c = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
                    pos_f = sorted_c[0][0]
                    neg_f = sorted_c[-1][0]
                    pos_val = float((rfm if pos_f in rfm else cust).get(pos_f, 0))
                    neg_val = float((rfm if neg_f in rfm else cust).get(neg_f, 0))
                    st.info(
                        f"This recommendation is driven most positively by **{pos_f}** ({pos_val:.1f}) "
                        f"and most negatively by **{neg_f}** ({neg_val:.1f})."
                    )
            except Exception:
                pass

            chart_df = breakdown.set_index("action_label")[["exploit", "explore"]]
            st.bar_chart(chart_df, color=["#0f766e", "#cbd5e1"], horizontal=True, height=320)

            with st.expander("Raw per-action scores"):
                detail = breakdown[["action_label", "exploit", "explore", "ucb_score", "cost"]].rename(columns={
                    "action_label": "Action",
                    "exploit": "Learned value",
                    "explore": "Uncertainty bonus",
                    "ucb_score": "UCB score",
                    "cost": "Cost",
                })
                st.dataframe(detail, hide_index=True, width="stretch")
    else:
        st.info("Pick a customer ID and click **Predict action** to see the per-action score breakdown.")
