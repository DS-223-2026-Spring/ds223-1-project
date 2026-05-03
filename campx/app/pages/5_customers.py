"""
Page 5 — Customer Explorer  (NEW for M3)
Owner: Armine Babajanyan (frontend branch)

Browses every customer with rich filtering, then drills into one
customer's detail (RFM + interaction history).

Wired to:
  GET /customers
  GET /customers/{id}        ← optional ?debug=true to peek latents

Built-in Streamlit components only.
"""
import pandas as pd
import streamlit as st

import bandit_utils as bu

st.set_page_config(page_title="Customers · CampX", layout="wide")

st.title("Customer Explorer")
st.caption("Browse the customer pool, filter by segment & RFM features, drill into one profile.")

# ── Load list ──────────────────────────────────────────────────
try:
    customers = bu.list_customers()
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

if customers.empty:
    st.info("No customers in the database yet. Have DS run customer generation.")
    st.stop()

# ── Top-level KPIs ─────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total customers", f"{len(customers):,}")
if "segment_label" in customers:
    k2.metric("Segments", customers["segment_label"].nunique())
if "monetary" in customers:
    k3.metric("Avg monetary", f"£{customers['monetary'].mean():.2f}")
if "frequency" in customers:
    k4.metric("Avg frequency", f"{customers['frequency'].mean():.2f}")

st.divider()

# ── Filters ────────────────────────────────────────────────────
st.subheader("Filters")

f1, f2, f3 = st.columns([1, 1, 2])
with f1:
    segments = sorted(customers["segment_label"].dropna().unique().tolist()) \
        if "segment_label" in customers else []
    selected_segments = st.multiselect(
        "Segment",
        options=segments,
        default=segments,
    )
with f2:
    genders = sorted(customers["gender"].dropna().unique().tolist()) \
        if "gender" in customers else []
    selected_genders = st.multiselect(
        "Gender",
        options=genders,
        default=genders,
    )
with f3:
    name_search = st.text_input(
        "Customer ID search",
        placeholder="exact ID, e.g. 42",
    )

f4, f5 = st.columns(2)
with f4:
    if "recency" in customers:
        rec_min = float(customers["recency"].min())
        rec_max = float(customers["recency"].max())
        rec_range = st.slider(
            "Recency range",
            min_value=rec_min, max_value=rec_max,
            value=(rec_min, rec_max),
        )
    else:
        rec_range = None
with f5:
    if "monetary" in customers:
        mon_min = float(customers["monetary"].min())
        mon_max = float(customers["monetary"].max())
        mon_range = st.slider(
            "Monetary range (£)",
            min_value=mon_min, max_value=mon_max,
            value=(mon_min, mon_max),
        )
    else:
        mon_range = None

# Apply filters
filtered = customers.copy()
if selected_segments and "segment_label" in filtered:
    filtered = filtered[filtered["segment_label"].isin(selected_segments)]
if selected_genders and "gender" in filtered:
    filtered = filtered[filtered["gender"].isin(selected_genders)]
if rec_range and "recency" in filtered:
    filtered = filtered[
        (filtered["recency"] >= rec_range[0]) &
        (filtered["recency"] <= rec_range[1])
    ]
if mon_range and "monetary" in filtered:
    filtered = filtered[
        (filtered["monetary"] >= mon_range[0]) &
        (filtered["monetary"] <= mon_range[1])
    ]
if name_search.strip():
    try:
        target_id = int(name_search.strip())
        filtered = filtered[filtered["customer_id"] == target_id]
    except ValueError:
        st.warning("Customer ID search expects a number.")

st.caption(f"Showing **{len(filtered):,}** of **{len(customers):,}** customers.")

st.divider()

# ── Segment distribution chart ─────────────────────────────────
if "segment_label" in filtered and not filtered.empty:
    st.subheader("Segment distribution")
    seg_counts = (
        filtered["segment_label"]
        .value_counts()
        .rename_axis("Segment")
        .to_frame("Customers")
    )
    st.bar_chart(seg_counts, height=260, y_label="Customers")
    st.divider()

# ── Customer table ─────────────────────────────────────────────
st.subheader("Customers")

if filtered.empty:
    st.info("No customers match the current filters.")
    st.stop()

display_cols = [c for c in [
    "customer_id", "segment_label", "gender",
    "recency", "frequency", "monetary",
    "basket_diversity", "avg_order_size", "purchase_regularity",
] if c in filtered.columns]

st.dataframe(
    filtered[display_cols],
    hide_index=True,
    width="stretch",
    column_config={
        "customer_id": "ID",
        "segment_label": "Segment",
        "gender": "Gender",
        "recency": st.column_config.NumberColumn("Recency", format="%.1f"),
        "frequency": st.column_config.NumberColumn("Frequency", format="%.1f"),
        "monetary": st.column_config.NumberColumn("Monetary (£)", format="%.2f"),
        "basket_diversity": st.column_config.NumberColumn("Basket div.", format="%.2f"),
        "avg_order_size": st.column_config.NumberColumn("Avg order", format="%.2f"),
        "purchase_regularity": st.column_config.NumberColumn("Regularity", format="%.2f"),
    },
)

st.divider()

# ── Customer detail ────────────────────────────────────────────
st.subheader("Customer detail")

selector_col, debug_col = st.columns([3, 1])
with selector_col:
    selected_id = st.selectbox(
        "Pick a customer",
        options=filtered["customer_id"].tolist(),
        format_func=lambda x: f"#{x}",
    )
with debug_col:
    show_latents = st.toggle(
        "Show latent traits",
        value=False,
        help="Adds ?debug=true to expose generative latents (DS-only).",
    )

try:
    detail = bu.get_customer(int(selected_id), debug=show_latents)
except bu.APIError as exc:
    bu.render_api_error(exc)
    st.stop()

# Profile block
profile_cols = st.columns(4)
profile_cols[0].metric("Customer ID", detail.get("customer_id"))
profile_cols[1].metric("Segment", detail.get("segment_label", "—"))
profile_cols[2].metric("Gender", detail.get("gender", "—"))

rfm = detail.get("rfm") or {}
if rfm:
    st.markdown("**RFM features**")
    rfm_df = pd.DataFrame([rfm])
    st.dataframe(rfm_df, hide_index=True, width="stretch")

if show_latents and "latents" in detail and detail["latents"]:
    with st.expander("Latent traits (debug)"):
        st.json(detail["latents"])

interactions = detail.get("interactions") or []
if interactions:
    st.markdown(f"**Interaction history** ({len(interactions)} rows)")
    inter_df = pd.DataFrame(interactions)
    if "decision_at" in inter_df:
        inter_df["decision_at"] = pd.to_datetime(
            inter_df["decision_at"], errors="coerce", utc=True
        ).dt.tz_localize(None).dt.strftime("%Y-%m-%d %H:%M")
    if "action" in inter_df:
        inter_df["action"] = inter_df["action"].map(
            lambda a: bu.ACTION_LABELS.get(a, a)
        )
    if "revenue" in inter_df:
        inter_df["revenue"] = inter_df["revenue"].apply(
            lambda x: f"£{x:.2f}" if pd.notna(x) else "—"
        )
    if "reward" in inter_df:
        inter_df["reward"] = inter_df["reward"].apply(
            lambda x: f"£{x:+.2f}" if pd.notna(x) else "—"
        )
    show_cols = [c for c in [
        "interaction_id", "simulation_id", "decision_at",
        "action", "converted", "revenue", "reward",
    ] if c in inter_df.columns]
    st.dataframe(inter_df[show_cols], hide_index=True, width="stretch")
else:
    st.caption("This customer has no interactions yet.")