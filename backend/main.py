"""
FastAPI Backend — Campaign Optimization Engine
Owner: Victoria Makaryan (backend branch)

Tasks (#43–#49):
  M2: Verify Swagger loads at /docs, all routes return placeholder responses
  M3: Implement /decide, /feedback, /metrics connected to DB and model
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Campaign Optimization Engine",
    description="LinUCB contextual bandit for promotional action selection",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "service": "campaign-api"}


@app.get("/customers", tags=["customers"])
def get_customers():
    # TODO (Victoria M3): connect to DB via crud.py
    return {"message": "not implemented yet — M3"}


@app.get("/customers/{customer_id}", tags=["customers"])
def get_customer(customer_id: int):
    # TODO (Victoria M3): connect to DB via crud.py
    return {"message": "not implemented yet — M3", "customer_id": customer_id}


@app.post("/decide", tags=["bandit"])
def decide(customer_id: int):
    # TODO (Victoria M3): load context, call LinUCB, log interaction
    return {"message": "not implemented yet — M3", "customer_id": customer_id}


@app.post("/feedback", tags=["bandit"])
def feedback(interaction_id: int, converted: bool, revenue: float):
    # TODO (Victoria M3): observe outcome, update model
    return {"message": "not implemented yet — M3"}


@app.get("/metrics", tags=["metrics"])
def get_metrics(simulation_id: int):
    # TODO (Victoria M3): aggregate from interactions table
    return {"message": "not implemented yet — M3"}


@app.get("/simulations", tags=["simulations"])
def list_simulations():
    # TODO (Victoria M3): read from simulations table
    return {"message": "not implemented yet — M3"}


@app.post("/simulate", tags=["simulations"])
def run_simulation(sim_name: str, num_rounds: int = 1000, alpha: float = 0.5):
    # TODO (Victoria M3): create simulation record, trigger Prefect flow
    return {"message": "not implemented yet — M3"}