# Demo

# CampX — Campaign Optimization Engine
**Course:** DS 223 Marketing Analytics — Group 1, Spring 2026

---

## Product Overview

**Product Name:** CampX — Campaign Optimization Engine  
**Course:** DS 223 Group Project

CampX is a contextual bandit system that learns which promotional 
action maximises net profit for each customer profile in a fashion 
retail setting. It replaces static rule-based promotion logic with 
an adaptive model that improves with every observed interaction.

---

## Problem Definition

E-commerce marketing teams allocate promotional budgets across 
customer segments using fixed rules or periodic A/B tests. This 
approach is slow to adapt, wastes budget on non-converting customers, 
and cannot personalise decisions at the individual level.

CampX addresses suboptimal promotional allocation — the gap between 
what a customer would respond to and what they actually receive — 
using a LinUCB contextual bandit that balances exploration of 
uncertain actions with exploitation of learned preferences.

**Promotional actions:** No action · Discount · Free shipping · 
Product recommendation · Bundle offer

---

## Solution Architecture

**Microservice Components:**

- **Frontend:** Streamlit interface for creating simulations, 
  monitoring interactions, inspecting model state, and exploring 
  customer profiles.
- **Backend:** FastAPI service exposing 8 endpoints covering 
  simulation lifecycle, real-time decision scoring, feedback 
  collection, and analytics aggregation.
- **Database:** PostgreSQL storing customers, interactions, 
  model state (theta/A/b matrices), and simulation records.
- **Data Science:** LinUCB implementation with synthetic customer 
  generation, RFM feature engineering, baseline comparisons, 
  and reproducibility verification.
- **Documentation:** MkDocs site with module-level docs and 
  governance guidelines.

---

## Live Demo Flow

### 1. Product Overview
- Problem statement and business cost of suboptimal allocation
- MVP scope: 5 actions, RFM context, single simulation at a time
- Architecture diagram and service interaction map

### 2. Frontend
- Navigate through the 5-page Streamlit interface
- Create a new simulation: set rounds, customer pool size, alpha
- Watch the Interaction page update as the background loop runs
- Review the Analytics page: cumulative reward curve, 
  conversion by action, segment performance table
- Inspect the Model page: theta heatmap, per-customer UCB preview
- Explore the Customer page: filter by RFM segment

### 3. Backend
- FastAPI endpoints and Swagger documentation at `/docs`
- POST `/simulations` → triggers background simulation loop
- POST `/decide` → LinUCB scoring with exploit/explore breakdown
- POST `/feedback` → weight update and model_state upsert
- GET `/metrics` → cumulative series, action distribution, 
  conversion rates

### 4. Database
- Schema: customers, customer_latents, interactions, 
  model_state, simulations, actions
- views: view_customer_with_latents, view_simulation_summary
- Stored procedures: sp_log_interaction, sp_submit_feedback
- Example records: 5000 interactions from a completed 
  simulation run, 200 customers with RFM + latent traits

### 5. Documentation
- MkDocs site: problem definition, modeling approach, 
  API contract, frontend structure, governance
- GitHub Pages: [link]
- Demo script: this page

---

## Final Notes

Use this page as the demo script and keep implementation 
details in the module-specific tabs.

**Fallback:** If live simulation is slow, select the existing 
5000-round simulation from the sidebar — all charts populate 
instantly from real data already in the database.