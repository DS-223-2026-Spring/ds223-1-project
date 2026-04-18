# Campaign Optimization Engine

**DS 223 · Marketing Analytics · Group 1 · Spring 2026 · AUA**

An AI-driven marketing decision system that uses **contextual bandits (LinUCB)** to select the optimal promotional action for each customer in real time — learning which offer works best for which customer segment as interactions accumulate.

---

## What it does

Given a customer's behavioral context (RFM features, basket diversity, purchase regularity), the system selects one of five promotional arms:

| Action | Description |
|--------|-------------|
| `no_action` | Control — no promotion |
| `discount_10` | 10% discount offer |
| `free_shipping` | Free shipping offer |
| `product_recommendation` | Personalized product recommendation |
| `bundle_offer` | Cross-sell bundle at a slight discount |

The LinUCB algorithm balances exploration (trying less-tested actions) with exploitation (choosing actions known to convert well), updating its model after each interaction.

---

## Team

| Role | Member | Branch |
|------|--------|--------|
| Product / Project Manager | Anna Asatryan | `pm` |
| DB Developer | Hayk Alekyan | `db` |
| Backend Developer | Victoria Makaryan | `backend` |
| Frontend Developer | Armine Babajanyan | `frontend` |
| Data Scientist | Davit Badalyan | `ds` |
| Orchestration Engineer | *(shared)* | `orchestration` |

---

## Quick start

```bash