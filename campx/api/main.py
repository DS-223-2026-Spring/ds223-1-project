from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import customers, bandit, simulations

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


app.include_router(customers.router)
app.include_router(bandit.router)
app.include_router(simulations.router)
