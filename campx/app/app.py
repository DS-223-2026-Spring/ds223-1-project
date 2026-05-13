"""
Campaign Optimization Engine — Streamlit entry point.
Owner: Armine Babajanyan (frontend branch)
"""

import base64
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import bandit_utils as bu


# ─────────────────────────────────────────────────────────────────────────────
# Paths / assets
# ─────────────────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent
ASSETS_DIR = APP_DIR / "assets"

CAMPAIGN_IMAGE = ASSETS_DIR / "campaign_flow.png"
LOGO_IMAGE = ASSETS_DIR / "campx_logo.png"


def image_to_base64(path: Path) -> str:
    """Convert an image file to base64 for inline HTML rendering."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return ""


logo_b64 = image_to_base64(LOGO_IMAGE)


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CampX",
    page_icon=str(LOGO_IMAGE) if LOGO_IMAGE.exists() else "📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

bu.render_sidebar_and_css()


# Keep page wide, but not absurdly stretched.
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1420px;
        padding-top: 3rem;
        padding-bottom: 4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────────────────────────────────────
def render_campaign_hero() -> None:
    """Render the CampX hero with text on the left and logo on the right."""

    logo_html = ""
    if logo_b64:
        logo_html = f"""
        <div class="cx-logo-panel">
            <img class="cx-logo" src="data:image/png;base64,{logo_b64}" alt="CampX logo" />
        </div>
        """

    html = textwrap.dedent(
        f"""
        <style>
        .cx-hero {{
            position: relative;
            width: 100%;
            margin: 0.75rem 0 1.85rem 0;
            border: 1px solid rgba(15, 118, 110, 0.14);
            border-radius: 24px;
            background:
                radial-gradient(circle at 86% 24%, rgba(20, 184, 166, 0.16), transparent 30%),
                radial-gradient(circle at 12% 92%, rgba(15, 118, 110, 0.055), transparent 28%),
                linear-gradient(135deg, #ffffff 0%, #f8fafc 54%, #eef7f6 100%);
            box-shadow: 0 16px 42px rgba(15, 23, 42, 0.065);
            overflow: hidden;
        }}

        .cx-hero-inner {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) 170px;
            align-items: center;
            gap: 2.75rem;
            min-height: 265px;
            padding: 2.45rem 3rem;
            box-sizing: border-box;
        }}

        .cx-copy {{
            min-width: 0;
            max-width: 780px;
        }}

        .cx-kicker {{
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.16em;
            color: #0f766e;
            margin-bottom: 0.72rem;
            text-transform: uppercase;
        }}

        .cx-title {{
            font-size: 3rem;
            font-weight: 850;
            color: #0f172a;
            line-height: 1.05;
            margin-bottom: 0.95rem;
            letter-spacing: -0.04em;
        }}

        .cx-title-x {{
            color: #0f766e;
            font-weight: 900;
        }}

        .cx-subtitle {{
            font-size: 1.03rem;
            color: #334155;
            line-height: 1.58;
            max-width: 740px;
        }}

        .cx-logo-panel {{
            justify-self: end;
            align-self: center;
            width: 136px;
            height: 136px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .cx-logo {{
            width: 122px;
            height: 122px;
            object-fit: cover;
            display: block;
            border-radius: 50%;
            clip-path: circle(49% at 50% 50%);
            filter: drop-shadow(0 14px 26px rgba(15, 23, 42, 0.16));
        }}

        @media (max-width: 900px) {{
            .cx-hero-inner {{
                grid-template-columns: 1fr;
                min-height: auto;
                padding: 1.8rem 1.5rem;
                gap: 1.15rem;
            }}

            .cx-title {{
                font-size: 2.25rem;
            }}

            .cx-subtitle {{
                font-size: 0.96rem;
                max-width: 100%;
            }}

            .cx-logo-panel {{
                justify-self: start;
                width: 86px;
                height: 86px;
            }}

            .cx-logo {{
                width: 78px;
                height: 78px;
            }}
        }}
        </style>

        <div class="cx-hero">
            <div class="cx-hero-inner">
                <div class="cx-copy">
                    <div class="cx-kicker">CAMPAIGN OPTIMIZATION ENGINE</div>
                    <div class="cx-title">Camp<span class="cx-title-x">X</span></div>
                    <div class="cx-subtitle">
                        CampX helps marketing teams choose the right promotion for each customer.
                        It learns from customer behavior and campaign outcomes to reduce wasted discounts,
                        test uncertain actions, and improve campaign profitability over time.
                    </div>
                </div>

                {logo_html}
            </div>
        </div>
        """
    )

    if hasattr(st, "html"):
        st.html(html)
    else:
        components.html(html, height=330, scrolling=False)


# ─────────────────────────────────────────────────────────────────────────────
# Top layout
# ─────────────────────────────────────────────────────────────────────────────
render_campaign_hero()

st.write("")
bu.render_top_navigation()
st.write("")


# ─────────────────────────────────────────────────────────────────────────────
# KPI tiles
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("System status")

try:
    sims = bu.list_simulations()
except bu.APIError as exc:
    bu.render_api_error(exc)
    sims = pd.DataFrame()

try:
    customers = bu.list_customers()
    customer_count = len(customers)
except bu.APIError:
    customer_count = 0

total_sims = len(sims)
running = int((sims["status"] == "running").sum()) if total_sims and "status" in sims else 0
best = sims["cumulative_reward"].max() if total_sims and "cumulative_reward" in sims else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Simulations run", total_sims)
c2.metric("Currently running", running)
c3.metric("Best cumulative reward", bu.format_currency(best))
c4.metric("Customer pool", customer_count)

st.write("")
st.write("")


# ─────────────────────────────────────────────────────────────────────────────
# Action catalog
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Action catalog")
st.write("The five promotional actions CampX can assign at each customer decision point.")

intended_segments = [
    "Likely buyers — avoid unnecessary incentives",
    "Price-sensitive or lapsed customers",
    "Moderate-intent basket planners",
    "Loyal, engaged browsers",
    "Impulse buyers with basket diversity",
]

action_df = pd.DataFrame(
    [
        {
            "Action": bu.ACTION_LABELS[k],
            "Cost to brand": bu.format_currency(v),
            "Intended segment": segment,
        }
        for (k, v), segment in zip(bu.ACTION_COSTS.items(), intended_segments)
    ]
)

st.dataframe(action_df, hide_index=True, width="stretch")

st.write("")
st.write("")


# ─────────────────────────────────────────────────────────────────────────────
# Bottom campaign-flow visual
# ─────────────────────────────────────────────────────────────────────────────
if CAMPAIGN_IMAGE.exists():
    st.image(str(CAMPAIGN_IMAGE), use_container_width=True)
else:
    st.caption("Campaign flow image not found. Expected: app/assets/campaign_flow.png")