# DS223 Marketing Analytics — Group Project Demo

## Product Overview

**Product Name:** CampX  
**Course:** DS223 Marketing Analytics — Group Project  
**Project Type:** Marketing Analytics MVP

CampX is a promotional campaign decision-support MVP. It helps illustrate how a marketing team could use customer behavior data to choose among different promotional action types and track the resulting campaign value.

In this project, each synthetic retail customer has RFM-style features such as recency, frequency, monetary value, basket diversity, average order size, and purchase regularity. Based on those features, CampX evaluates five possible promotional actions: no action, 10% discount, free shipping, product recommendation, and bundle offer.

The system is built as an end-to-end microservice application: a Python data science workflow generates synthetic campaign data and LinUCB model outputs, PostgreSQL stores the results, FastAPI exposes the backend contract, and Streamlit presents the dashboard. The project uses synthetic data, so the goal is to demonstrate architecture, integration, and decision-support logic rather than claim validated business lift on real customers.

---

## Problem Definition

Marketing teams often need to decide which offer or promotional action should be shown to each customer. Sending the same discount to everyone can waste budget, reduce margins, and ignore differences in customer behavior.

Different customer profiles may respond differently:

- Some customers may need a discount.
- Some may respond to free shipping.
- Some may engage with a recommendation or bundle.
- Some may convert without any promotion.

CampX frames this as a campaign optimization problem: use customer context to select a promotional action type and evaluate the result using simulated revenue minus promotional cost.

---

## Solution Architecture

CampX is implemented as a containerized microservice-style project.

### Microservice Components

| Component | Technology | Role in the MVP |
|---|---|---|
| Frontend | Streamlit | User-facing dashboard for campaign setup, live decisions, performance, model behavior, and customers |
| Backend | FastAPI | API layer exposing application logic, campaign metrics, customers, actions, model state, and baselines |
| Database | PostgreSQL | Storage for customers, actions, simulations, interactions, model state, and artifacts |
| Data Science | Python | Synthetic data generation, LinUCB-style contextual bandit logic, baselines, and reproducibility outputs |
| Documentation | MkDocs | Project documentation, architecture notes, API overview, and module-specific explanations |

### Data Flow

```text
Data Science pipeline → PostgreSQL → FastAPI → Streamlit dashboard
```

The DS pipeline creates synthetic customer profiles, campaign interactions, model state, and output artifacts. PostgreSQL stores these outputs. FastAPI exposes them through documented endpoints. Streamlit consumes the API responses and presents the campaign workflow to the user.

---

## Live Demo Flow

### 1. Product Overview

CampX addresses a common marketing decision: which promotional action should be shown to which customer. A single blanket discount can be wasteful because customers differ in purchase history, price sensitivity, loyalty, and likely response to incentives.

The MVP focuses on **promotional action-type selection**. Given synthetic retail customer profiles with RFM-style features, CampX evaluates five possible actions: no action, 10% discount, free shipping, product recommendation, and bundle offer. The outcome is measured as simulated net campaign value:

```text
reward = simulated realized revenue - promotional action cost

The system is implemented as a runnable microservice MVP. The Python DS workflow generates synthetic customers, LinUCB campaign interactions, model state, baselines, and artifacts. PostgreSQL stores the campaign data. FastAPI exposes the data and decision endpoints. Streamlit presents the campaign dashboard. MkDocs documents the product, architecture, API, database, and modeling assumptions.
```

---

### 2. Frontend

The Streamlit frontend presents the product experience.

![CampX streamlit landing page](images/campx_home.png) 

<http://localhost:8501>


Main pages:

| Page | Purpose |
|---|---|
| Home | Product overview and service summary |
| Campaign Setup | Campaign-run configuration and existing run selection |
| Live Decisions | Round-level campaign decisions and recent interactions |
| Performance | Cumulative campaign value, baseline comparison, action distribution, conversion, reward, and segment performance |
| Decision Logic | Model-state inspection and action-score breakdown |
| Customers | Customer profiles, RFM-style features, segments, and interaction history |

The frontend is intended to make the system understandable to a marketing analyst rather than only to a developer.

---

### 3. Backend

The FastAPI backend acts as the contract layer between the frontend, database, and data science outputs.

<http://localhost:8000/docs>

Representative endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Confirms backend availability |
| `GET /actions` | Returns the promotional action definitions |
| `GET /customers` | Returns synthetic customer profiles |
| `GET /simulations` | Lists campaign runs |
| `GET /metrics` | Provides dashboard-ready campaign metrics |
| `GET /model/state` | Provides model-state information for decision logic |
| `POST /decide` | Returns an action recommendation or preview for a customer |
| `GET /baselines` | Returns baseline comparison data |
| `POST /simulations/{simulation_id}/step` | Advances one campaign decision step for incremental simulation |

The backend exposes Swagger documentation through FastAPI and provides a clear request-response interface for the frontend.

---

### 4. Database

PostgreSQL stores the core entities used by the MVP.

Main database objects:

| Object | Purpose |
|---|---|
| `customers` | Synthetic customer profile features |
| `customer_latents` | Simulation-only hidden variables used for synthetic outcome generation |
| `actions` | Promotional action definitions and costs |
| `simulations` | Campaign-run metadata |
| `interactions` | Round-level decisions, conversions, revenue, costs, and rewards |
| `model_state` | Stored model-state outputs |
| `simulation_artifacts` | Data science artifacts and output references |

The database supports the full path from generated customer data to dashboard metrics.

### ERD

![CampX database schema](images/campx_erd.png)

---

### 5. Documentation

MkDocs is used to document the project structure, service responsibilities, data model, API contract, data science pipeline, and demo flow.

Documentation sections include:

- Product overview
- Backend API
- Database
- Data science/modeling
- Frontend app
- Integration map
- Docker/local run notes
- Demo overview

<https://ds-223-2026-spring.github.io/ds223-1-project/>

The deployed documentation provides a central reference for understanding both the product concept and the implementation.

---

## Final Notes

CampX is a course MVP. Its value is in demonstrating a working, integrated marketing analytics system rather than claiming production readiness.

Important scope boundaries:

- Data is synthetic retail-style data.
- Reward is simulated revenue minus promotional action cost.
- The model selects promotional action types, not exact product SKUs or exact bundles.
- Product and bundle tables are included as catalog scaffolding for future item-level personalization.
- Dedicated workflow scheduling is out of final MVP scope.
- The current system is intended for demo and educational purposes, not real campaign deployment.
