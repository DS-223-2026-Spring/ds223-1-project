# CampX — Campaign Optimization Engine

**DS 223 · Marketing Analytics · Group 1 · Spring 2026 · AUA**

A contextual bandit system (LinUCB) that selects the optimal promotional action
for each fashion retail customer — learning which offer maximises net profit for
which customer profile, updating automatically after every interaction.

---

## The problem

Fashion retailers send the same promotion to every customer. Champions who buy
regardless get a 10% discount they didn't need. Lost customers get free shipping
on a product they don't want. Budget is wasted. Margin is destroyed. Nothing learns.

## The solution

Match the right promotional action to the right customer at the right moment —
and improve automatically as interactions accumulate. No human rewrites rules.
No retraining cycles. The model updates itself after every single decision.

## Domain

Online fashion retail — men and women, mid-market price range (avg order £65).

| Action | Cost to brand | Works on |
|--------|--------------|----------|
| No action | £0.00 | Champions — buy regardless |
| 10% discount | £6.50 | Price-sensitive, lapsed customers |
| Free shipping | £4.99 | Moderate-basket planners |
| Product recommendation | £0.30 | Loyal, engaged browsers |
| Bundle offer | £9.00 | Impulse buyers with basket diversity |

---

## Data strategy

Fully simulated — no external dataset. Three latent traits per customer
(price sensitivity, brand loyalty, impulse tendency) are drawn once at
generation time and drive both observable RFM features and action-specific
conversion probability. LinUCB observes only RFM — never the latents.
This is what makes the learning problem genuinely non-trivial.

---

## Team

| Role | Member | Branch |
|------|--------|--------|
| PM | Anna Asatryan | `pm` |
| DB Developer | Hayk Alekyan | `db` |
| Backend | Victoria Makaryan | `backend` |
| Frontend | Armine Babajanyan | `frontend` |
| Data Scientist | Davit Badalyan | `ds` |
| Orchestration | *(shared)* | `orchestration` |

---

## Quick start


1. **Setup environment variables:**
```bash
cp .env.example .env
```

2. **Launch services:**
```bash
docker-compose up --build
```


| Service | URL |
|---------|-----|
| Streamlit dashboard | http://localhost:8502 |
| FastAPI docs | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 — admin@admin.com / admin123 |
| Prefect UI | http://localhost:4200 |

---

## Milestones

| Milestone | Due | Focus |
|-----------|-----|-------|
| M1 | Apr 12 | Problem definition, roles, roadmap, prototype |
| M2 | Apr 21 | DB schema, customer generation, LinUCB |
| M3 | May 1 | API, Streamlit, Prefect integration |
| M4 | May 8 | Testing, documentation, polish |
| Demo | May 14 | Live demonstration |