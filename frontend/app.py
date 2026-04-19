"""Streamlit main entry point.
Owner: Armine Babajanyan (frontend branch)

Tasks (#52–#57):
  M2: Navigation skeleton, placeholder layout sections
  M3: Connect to API, implement all 4 pages with real data

Pages:
  1_simulation.py    — run and configure simulations
  2_dashboard.py     — live cumulative reward + action distribution
  3_customers.py     — browse customer profiles and segments
  4_model_inspector.py — inspect LinUCB θ vectors and n_pulls
"""
import streamlit as st

st.set_page_config(page_title="Campaign Optimization Engine", layout="wide")
st.title("Campaign Optimization Engine")
st.write("Dashboard placeholder — implement in M3.")
