# Backend API — FastAPI

**Owner:** Victoria Makaryan · Branch: `backend`

---

## Overview

RESTful API built with FastAPI, serving the LinUCB model and exposing CRUD operations on the database.

**Base URL:** `http://localhost:8000`  
**Interactive docs:** `http://localhost:8000/docs`

---

## Planned endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/customers` | List all customers |
| `POST` | `/customers` | Add a new customer |
| `GET` | `/predict/{customer_id}` | Get best action for a customer |
| `POST` | `/interact` | Log an interaction and update model |
| `GET` | `/actions` | List all available actions |
| `GET` | `/simulations` | List simulation runs |
| `POST` | `/simulate` | Trigger a new simulation run |
| `GET` | `/model/state` | Inspect current LinUCB matrices |

---

## Setup

```bash
docker-compose up api
```

*(Full implementation — M3)*